from __future__ import annotations

import hashlib
import json
from typing import Any


def render_context_packet(context: dict[str, Any]) -> str:
    """Render a compact packet that can be pasted into a normal ChatGPT chat."""

    payload = json.dumps(context, ensure_ascii=False, indent=2)
    return (
        "LEARNINGFLOW_CONTEXT_V1\n"
        "Use this as prior learning evidence, not as proof of mastery. "
        "Do not reveal any server-side answer key because none is included.\n"
        f"{payload}\n"
    )


def prepare_record_packet(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize a manually transported ChatGPT evidence packet.

    Manual copy/paste should not require the model to invent a reliable UUID.
    When the packet has no idempotency key, derive one from its stable content
    so re-pasting the exact same packet does not duplicate evidence.
    """

    required = {"student_id", "data_mode", "purpose", "capture_mode", "items"}
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"record packet missing fields: {', '.join(missing)}")

    normalized = dict(payload)
    if not str(normalized.get("idempotency_key") or "").strip():
        stable = {
            "student_id": normalized["student_id"],
            "data_mode": normalized["data_mode"],
            "purpose": normalized["purpose"],
            "capture_mode": normalized["capture_mode"],
            "items": normalized["items"],
            "session_id": normalized.get("session_id"),
            "surface": normalized.get("surface", "chatgpt"),
        }
        encoded = json.dumps(
            stable,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        normalized["idempotency_key"] = f"manual-{hashlib.sha256(encoded).hexdigest()[:24]}"
    normalized.setdefault("surface", "chatgpt")
    return normalized


def parse_record_packet(text: str) -> dict[str, Any]:
    """Parse a JSON evidence packet copied from ChatGPT."""

    text = text.strip()
    if text.startswith("```json") and text.endswith("```"):
        text = text[7:-3].strip()
    elif text.startswith("```") and text.endswith("```"):
        text = text[3:-3].strip()
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("record packet must be a JSON object")
    return prepare_record_packet(payload)
