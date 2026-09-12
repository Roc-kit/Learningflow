from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from learningflow.transcripts import CodexTranscriptAdapter, TRANSCRIPT_SCHEMA


class CodexTranscriptAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.codex_home = self.root / ".codex"
        session_dir = self.codex_home / "sessions" / "2026" / "09" / "12"
        session_dir.mkdir(parents=True)
        self.session_id = "11111111-2222-3333-4444-555555555555"
        self.rollout = session_dir / f"rollout-2026-09-12T20-00-00-{self.session_id}.jsonl"
        rows = [
            {
                "timestamp": "2026-09-12T12:00:00Z",
                "type": "session_meta",
                "payload": {
                    "id": self.session_id,
                    "session_id": self.session_id,
                    "timestamp": "2026-09-12T12:00:00Z",
                    "originator": "Codex Desktop",
                    "source": "vscode",
                    "cwd": "/tmp/example",
                },
            },
            self._message("dev", "developer", "input_text", "hidden system instruction"),
            self._message(
                "host",
                "user",
                "input_text",
                "<environment_context>hidden host context</environment_context>",
                content_kind="environments.environment_context",
            ),
            self._message("u1", "user", "input_text", "Does Tom like cats?"),
            {
                "timestamp": "2026-09-12T12:00:02Z",
                "type": "response_item",
                "payload": {"type": "reasoning", "summary": [{"text": "hidden chain"}]},
            },
            self._message("a1", "assistant", "output_text", "Yes. Now explain why."),
            {
                "timestamp": "2026-09-12T12:00:04Z",
                "type": "response_item",
                "payload": {"type": "custom_tool_call", "name": "shell", "arguments": "secret"},
            },
            self._message("u2", "user", "input_text", "Because Tom is one person."),
        ]
        self.rollout.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )
        (self.codex_home / "session_index.jsonl").write_text(
            json.dumps(
                {
                    "id": self.session_id,
                    "thread_name": "English practice",
                    "updated_at": "2026-09-12T12:00:04Z",
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _message(
        message_id: str,
        role: str,
        content_type: str,
        text: str,
        content_kind: str | None = None,
    ) -> dict:
        metadata = {"turn_id": f"turn-{message_id}"}
        if content_kind is not None:
            metadata["content_item_kinds"] = [content_kind]
        return {
            "timestamp": "2026-09-12T12:00:01Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "id": message_id,
                "role": role,
                "content": [{"type": content_type, "text": text}],
                "internal_chat_message_metadata_passthrough": metadata,
            },
        }

    def test_only_visible_user_and_assistant_text_is_exported(self) -> None:
        transcript = CodexTranscriptAdapter(self.codex_home).read_session(self.session_id)
        self.assertEqual(transcript["schema"], TRANSCRIPT_SCHEMA)
        self.assertEqual(transcript["title"], "English practice")
        self.assertEqual([row["role"] for row in transcript["messages"]], ["user", "assistant", "user"])
        text = json.dumps(transcript, ensure_ascii=False)
        self.assertNotIn("hidden system instruction", text)
        self.assertNotIn("hidden host context", text)
        self.assertNotIn("hidden chain", text)
        self.assertNotIn("secret", text)

    def test_sync_writes_local_normalized_transcript_idempotently(self) -> None:
        adapter = CodexTranscriptAdapter(self.codex_home)
        destination = self.root / "normalized"
        first = adapter.sync(destination)
        second = adapter.sync(destination)
        self.assertEqual(first["created"], 1)
        self.assertEqual(second["unchanged"], 1)
        saved = json.loads((destination / f"{self.session_id}.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["external_session_id"], self.session_id)


if __name__ == "__main__":
    unittest.main()
