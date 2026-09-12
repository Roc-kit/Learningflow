from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


TRANSCRIPT_SCHEMA = "learningflow.transcript.v1"


def default_codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


class CodexTranscriptAdapter:
    """Read only the visible user/assistant text from local Codex rollouts.

    Reasoning, developer messages, tool calls, tool results, shell output, and
    encrypted content are deliberately excluded. The adapter is a source
    normalizer, not a learning-evidence classifier.
    """

    def __init__(self, codex_home: Path | None = None):
        self.codex_home = codex_home or default_codex_home()

    def list_sessions(self, limit: int = 30) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        index = self._session_index()
        rollout_by_session: dict[str, Path] = {}
        for rollout in self._all_rollouts():
            session_id = self._session_id_from_rollout(rollout)
            rollout_by_session.setdefault(session_id, rollout)

        rows: list[dict[str, Any]] = []
        for session_id, rollout in rollout_by_session.items():
            meta = index.get(session_id, {})
            rows.append(
                {
                    "session_id": session_id,
                    "title": meta.get("thread_name"),
                    "updated_at": meta.get("updated_at") or self._mtime_iso(rollout),
                    "rollout_path": str(rollout),
                }
            )
        rows.sort(key=lambda row: row.get("updated_at") or "", reverse=True)
        return rows[:limit]

    def latest_session_id(self) -> str:
        sessions = self.list_sessions(limit=1)
        if sessions:
            return str(sessions[0]["session_id"])

        rollouts = self._all_rollouts()
        if not rollouts:
            raise FileNotFoundError("no Codex rollout files found")
        return self._session_id_from_rollout(rollouts[0])

    def resolve_rollout(self, session_id: str) -> Path | None:
        candidates = list(self.codex_home.glob(f"sessions/**/rollout-*{session_id}.jsonl"))
        candidates += list(self.codex_home.glob(f"archived_sessions/rollout-*{session_id}.jsonl"))
        if not candidates:
            return None
        return max(candidates, key=lambda path: path.stat().st_mtime)

    def read_session(self, session_id: str) -> dict[str, Any]:
        rollout = self.resolve_rollout(session_id)
        if rollout is None:
            raise FileNotFoundError(f"Codex session not found: {session_id}")
        return self.read_rollout(rollout)

    def read_rollout(self, rollout: Path) -> dict[str, Any]:
        meta: dict[str, Any] = {}
        messages: list[dict[str, Any]] = []
        seen_message_ids: set[str] = set()

        with rollout.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = row.get("payload")
                if not isinstance(payload, dict):
                    continue

                if row.get("type") == "session_meta" and not meta:
                    meta = payload
                    continue

                if row.get("type") != "response_item" or payload.get("type") != "message":
                    continue
                role = payload.get("role")
                if role not in {"user", "assistant"}:
                    continue

                message_id = str(payload.get("id") or "")
                if message_id and message_id in seen_message_ids:
                    continue
                if message_id:
                    seen_message_ids.add(message_id)

                expected_content_type = "input_text" if role == "user" else "output_text"
                text_parts: list[str] = []
                contents = payload.get("content") or []
                internal = payload.get("internal_chat_message_metadata_passthrough")
                kinds = internal.get("content_item_kinds") if isinstance(internal, dict) else None
                aligned_kinds = kinds if isinstance(kinds, list) and len(kinds) == len(contents) else None
                for index, content in enumerate(contents):
                    if not isinstance(content, dict) or content.get("type") != expected_content_type:
                        continue
                    if role == "user" and aligned_kinds is not None and aligned_kinds[index] != "user.text":
                        continue
                    text = content.get("text")
                    if isinstance(text, str) and text.strip():
                        text_parts.append(text.strip())
                if not text_parts:
                    continue

                turn_id = internal.get("turn_id") if isinstance(internal, dict) else None
                messages.append(
                    {
                        "message_id": message_id or None,
                        "turn_id": turn_id,
                        "role": role,
                        "text": "\n\n".join(text_parts),
                        "occurred_at": row.get("timestamp"),
                        "phase": payload.get("phase") if role == "assistant" else None,
                    }
                )

        session_id = str(meta.get("session_id") or meta.get("id") or self._session_id_from_rollout(rollout))
        index_meta = self._session_index().get(session_id, {})
        return {
            "schema": TRANSCRIPT_SCHEMA,
            "source": "codex",
            "external_session_id": session_id,
            "title": index_meta.get("thread_name"),
            "started_at": meta.get("timestamp"),
            "source_metadata": {
                "originator": meta.get("originator"),
                "source": meta.get("source"),
                "cwd": meta.get("cwd"),
                "rollout_path": str(rollout),
            },
            "messages": messages,
        }

    def sync(self, destination: Path, limit: int | None = None) -> dict[str, Any]:
        destination.mkdir(parents=True, exist_ok=True)
        sessions = self.list_sessions(limit=limit or 100000)
        created = updated = unchanged = 0
        written: list[str] = []

        for row in sessions:
            session_id = str(row["session_id"])
            transcript = self.read_session(session_id)
            target = destination / f"{session_id}.json"
            content = json.dumps(transcript, ensure_ascii=False, indent=2) + "\n"
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            old_digest = None
            if target.exists():
                old_digest = hashlib.sha256(target.read_bytes()).hexdigest()
            if old_digest == digest:
                unchanged += 1
                continue
            target.write_text(content, encoding="utf-8")
            written.append(str(target))
            if old_digest is None:
                created += 1
            else:
                updated += 1

        return {
            "source": "codex",
            "destination": str(destination),
            "created": created,
            "updated": updated,
            "unchanged": unchanged,
            "written": written,
        }

    def _session_index(self) -> dict[str, dict[str, Any]]:
        path = self.codex_home / "session_index.jsonl"
        result: dict[str, dict[str, Any]] = {}
        if not path.exists():
            return result
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                session_id = row.get("id")
                if isinstance(session_id, str) and session_id:
                    result[session_id] = row
        return result

    def _all_rollouts(self) -> list[Path]:
        paths = list(self.codex_home.glob("sessions/**/rollout-*.jsonl"))
        paths += list(self.codex_home.glob("archived_sessions/rollout-*.jsonl"))
        return sorted(paths, key=lambda path: path.stat().st_mtime, reverse=True)

    @staticmethod
    def _session_id_from_rollout(path: Path) -> str:
        return path.stem[-36:]

    @staticmethod
    def _mtime_iso(path: Path) -> str:
        from datetime import datetime, timezone

        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
