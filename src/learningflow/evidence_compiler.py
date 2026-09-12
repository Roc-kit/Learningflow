from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from .transcripts import TRANSCRIPT_SCHEMA


SELECTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["purpose", "items"],
    "properties": {
        "purpose": {"type": "string"},
        "items": {
            "type": "array",
            "maxItems": 20,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "prompt_message_id",
                    "response_message_id",
                    "question_type",
                    "result",
                    "reason",
                ],
                "properties": {
                    "prompt_message_id": {"type": "string"},
                    "response_message_id": {"type": "string"},
                    "question_type": {
                        "type": ["string", "null"],
                    },
                    "result": {
                        "type": "string",
                        "enum": ["correct", "incorrect", "partial", "unclear", "pending_review"],
                    },
                    "reason": {"type": "string"},
                },
            },
        },
    },
}


def build_compiler_prompt(transcript: dict[str, Any]) -> str:
    return """You are compiling durable learning evidence from a visible chat transcript.

Return only the JSON object required by the supplied output schema.

Rules:
- Select only genuine learner-assessment exchanges: an assistant message that asks a learner-facing question intended to check understanding, followed by a user message that is the learner's actual answer.
- Ordinary conversation, coding/project discussion, acknowledgements, requests to the assistant, and the assistant's own examples are not learning evidence.
- Use only message_id values present in the transcript. Do not rewrite the prompt or learner answer; the caller will recover the exact text by message ID.
- If one assistant message contains explanation plus one assessment question, it may still be selected.
- response_message_id must point to a user message occurring after the prompt message.
- If correctness is not defensible from the visible transcript, use pending_review or unclear. Do not guess hidden answer keys.
- Do not infer that the learner was unassisted. Assistance is handled separately by the caller.
- A single error does not prove a misconception or broad mastery state.
- purpose should be a short description of what the selected assessment block checks.
- It is valid to return an empty items array when the transcript contains no learning assessment.

Transcript:
""" + json.dumps(transcript, ensure_ascii=False, separators=(",", ":"))


def run_codex_selector(
    transcript: dict[str, Any], *, codex_bin: str = "codex"
) -> dict[str, Any]:
    """Use Codex CLI as a semantic selector over a normalized transcript."""

    if transcript.get("schema") != TRANSCRIPT_SCHEMA:
        raise ValueError("unsupported transcript schema")

    with tempfile.TemporaryDirectory(prefix="learningflow-compiler-") as temp:
        root = Path(temp)
        schema_path = root / "selection.schema.json"
        output_path = root / "selection.json"
        schema_path.write_text(
            json.dumps(SELECTION_SCHEMA, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                codex_bin,
                "exec",
                "--ephemeral",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "-C",
                str(root),
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
                "-",
            ],
            input=build_compiler_prompt(transcript),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown Codex failure"
            raise RuntimeError(f"Codex evidence compiler failed: {detail}")
        try:
            selection = json.loads(output_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise RuntimeError("Codex evidence compiler returned invalid structured output") from exc
    return selection


def selection_to_record_packet(
    transcript: dict[str, Any],
    selection: dict[str, Any],
    *,
    student_id: str,
    data_mode: str,
) -> dict[str, Any] | None:
    messages = transcript.get("messages")
    if not isinstance(messages, list):
        raise ValueError("transcript messages must be an array")
    by_id = {
        str(message.get("message_id")): (index, message)
        for index, message in enumerate(messages)
        if isinstance(message, dict) and message.get("message_id")
    }

    selected_items = selection.get("items")
    if not isinstance(selected_items, list):
        raise ValueError("compiler selection items must be an array")
    if not selected_items:
        return None

    packet_items: list[dict[str, Any]] = []
    source_pairs: list[tuple[str, str]] = []
    for selected in selected_items:
        if not isinstance(selected, dict):
            raise ValueError("compiler selection item must be an object")
        prompt_id = str(selected.get("prompt_message_id") or "")
        response_id = str(selected.get("response_message_id") or "")
        if prompt_id not in by_id or response_id not in by_id:
            raise ValueError("compiler selected a message ID outside the transcript")
        prompt_index, prompt = by_id[prompt_id]
        response_index, response = by_id[response_id]
        if prompt.get("role") != "assistant" or response.get("role") != "user":
            raise ValueError("compiler selected invalid prompt/response roles")
        if response_index <= prompt_index:
            raise ValueError("compiler selected a response that does not follow the prompt")

        source_pairs.append((prompt_id, response_id))
        packet_items.append(
            {
                "prompt": str(prompt["text"]),
                "question_type": selected.get("question_type"),
                "occurred_at": response.get("occurred_at"),
                "response": {
                    "raw_answer": str(response["text"]),
                    "input_modality": "text",
                    "source_quality": "direct_text",
                    "assistance_level": "unknown",
                },
                "assessment": {
                    "result": selected["result"],
                    "reason": selected.get("reason"),
                    "evaluation_method": "llm",
                },
            }
        )

    external_session_id = str(transcript.get("external_session_id") or "unknown")
    stable = json.dumps(source_pairs, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    digest = hashlib.sha256(stable).hexdigest()[:20]
    return {
        "student_id": student_id,
        "data_mode": data_mode,
        "purpose": str(selection.get("purpose") or "Transcript-derived assessment").strip(),
        "capture_mode": "batch_verbatim",
        "surface": "manual",
        "idempotency_key": f"codex-transcript-{external_session_id}-{digest}",
        "items": packet_items,
    }
