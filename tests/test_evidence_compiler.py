from __future__ import annotations

import unittest

from learningflow.evidence_compiler import selection_to_record_packet


class EvidenceCompilerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.transcript = {
            "schema": "learningflow.transcript.v1",
            "source": "codex",
            "external_session_id": "session-1",
            "messages": [
                {
                    "message_id": "a1",
                    "role": "assistant",
                    "text": "Does Tom ___ cats?",
                    "occurred_at": "2026-09-12T10:00:00Z",
                },
                {
                    "message_id": "u1",
                    "role": "user",
                    "text": "likes",
                    "occurred_at": "2026-09-12T10:00:05Z",
                },
                {
                    "message_id": "a2",
                    "role": "assistant",
                    "text": "Try again: Does Tom ___ cats?",
                    "occurred_at": "2026-09-12T10:00:10Z",
                },
                {
                    "message_id": "u2",
                    "role": "user",
                    "text": "like",
                    "occurred_at": "2026-09-12T10:00:15Z",
                },
            ],
        }

    def test_exact_transcript_text_is_used_not_model_rewrite(self) -> None:
        selection = {
            "purpose": "does 后动词原形",
            "items": [
                {
                    "prompt_message_id": "a1",
                    "response_message_id": "u1",
                    "question_type": "fill_blank",
                    "result": "incorrect",
                    "reason": "does 后应使用动词原形",
                }
            ],
        }
        packet = selection_to_record_packet(
            self.transcript, selection, student_id="child-test", data_mode="test"
        )
        assert packet is not None
        self.assertEqual(packet["items"][0]["prompt"], "Does Tom ___ cats?")
        self.assertEqual(packet["items"][0]["response"]["raw_answer"], "likes")
        self.assertEqual(packet["items"][0]["response"]["assistance_level"], "unknown")

    def test_selection_must_reference_assistant_then_user(self) -> None:
        selection = {
            "purpose": "bad pair",
            "items": [
                {
                    "prompt_message_id": "u1",
                    "response_message_id": "a2",
                    "question_type": None,
                    "result": "pending_review",
                    "reason": "invalid",
                }
            ],
        }
        with self.assertRaises(ValueError):
            selection_to_record_packet(
                self.transcript, selection, student_id="child-test", data_mode="test"
            )

    def test_empty_selection_is_not_written(self) -> None:
        packet = selection_to_record_packet(
            self.transcript,
            {"purpose": "none", "items": []},
            student_id="child-test",
            data_mode="test",
        )
        self.assertIsNone(packet)


if __name__ == "__main__":
    unittest.main()
