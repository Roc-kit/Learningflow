from __future__ import annotations

import json
import unittest

from learningflow.bridge import parse_record_packet, prepare_record_packet, render_context_packet


class BridgeTest(unittest.TestCase):
    def sample_packet(self) -> dict:
        return {
            "student_id": "child-test",
            "data_mode": "test",
            "purpose": "一般现在时短验证",
            "capture_mode": "batch_verbatim",
            "items": [
                {
                    "prompt": "Does Tom ___ cats?",
                    "response": {
                        "raw_answer": "like",
                        "input_modality": "text",
                        "source_quality": "direct_text",
                        "assistance_level": "none",
                    },
                    "assessment": {
                        "result": "correct",
                        "reason": "助动词后使用原形",
                        "evaluation_method": "llm",
                    },
                }
            ],
        }

    def test_manual_idempotency_key_is_stable(self) -> None:
        first = prepare_record_packet(self.sample_packet())
        second = prepare_record_packet(self.sample_packet())
        self.assertEqual(first["idempotency_key"], second["idempotency_key"])
        self.assertTrue(first["idempotency_key"].startswith("manual-"))

    def test_parse_accepts_json_code_fence(self) -> None:
        text = "```json\n" + json.dumps(self.sample_packet(), ensure_ascii=False) + "\n```"
        parsed = parse_record_packet(text)
        self.assertEqual(parsed["student_id"], "child-test")
        self.assertEqual(parsed["surface"], "chatgpt")

    def test_context_packet_marks_state_as_evidence(self) -> None:
        packet = render_context_packet(
            {
                "student": {"id": "child-test"},
                "recent_evidence": [],
                "state_notice": "no mastery state",
            }
        )
        self.assertTrue(packet.startswith("LEARNINGFLOW_CONTEXT_V1"))
        self.assertIn("not as proof of mastery", packet)


if __name__ == "__main__":
    unittest.main()
