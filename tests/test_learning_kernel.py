from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from learningflow.service import LearningService
from learningflow.storage import SQLiteStore


class LearningKernelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.service = LearningService(SQLiteStore(Path(self.tmp.name) / "learningflow.db"))
        self.service.ensure_student(
            student_id="child-test",
            display_name="测试学生",
            data_mode="test",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def sample_items(self) -> list[dict]:
        return [
            {
                "prompt": "Does Tom ___ cats?",
                "question_type": "fill_blank",
                "expected_answer": "like",
                "rubric": {"accept": ["like"]},
                "response": {
                    "raw_answer": "likes",
                    "input_modality": "text",
                    "source_quality": "direct_text",
                    "assistance_level": "none",
                },
                "assessment": {
                    "result": "incorrect",
                    "reason": "does 后应使用动词原形",
                    "evaluation_method": "llm",
                },
            },
            {
                "prompt": "Does Jack ___ football?",
                "question_type": "fill_blank",
                "expected_answer": "play",
                "response": {
                    "raw_answer": "play",
                    "input_modality": "voice",
                    "source_quality": "transcript",
                    "assistance_level": "light",
                },
                "assessment": {
                    "result": "correct",
                    "reason": "使用了助动词后的动词原形",
                    "evaluation_method": "llm",
                },
            },
        ]

    def test_record_and_read_context_without_answer_key_leak(self) -> None:
        saved = self.service.record_assessment_run(
            student_id="child-test",
            data_mode="test",
            purpose="does 后动词原形短验证",
            capture_mode="batch_verbatim",
            items=self.sample_items(),
            idempotency_key="run-001",
        )
        self.assertEqual(len(saved["saved_item_ids"]), 2)

        context = self.service.get_learning_context(
            student_id="child-test", data_mode="test", limit=10
        )
        self.assertEqual(len(context["recent_evidence"]), 2)
        self.assertEqual(context["recent_evidence"][0]["response"]["raw_answer"], "play")
        self.assertNotIn("expected_answer", context["recent_evidence"][0])
        self.assertNotIn("rubric", context["recent_evidence"][0])

    def test_idempotent_replay_does_not_duplicate_evidence(self) -> None:
        kwargs = dict(
            student_id="child-test",
            data_mode="test",
            purpose="短验证",
            capture_mode="batch_verbatim",
            items=self.sample_items(),
            idempotency_key="same-chat-fragment",
        )
        first = self.service.record_assessment_run(**kwargs)
        second = self.service.record_assessment_run(**kwargs)
        self.assertEqual(first["assessment_run_id"], second["assessment_run_id"])
        self.assertEqual(first["saved_item_ids"], second["saved_item_ids"])
        self.assertEqual(second["warnings"], ["idempotent_replay"])

        context = self.service.get_learning_context(
            student_id="child-test", data_mode="test", limit=10
        )
        self.assertEqual(len(context["recent_evidence"]), 2)

    def test_test_real_boundary_is_enforced(self) -> None:
        with self.assertRaisesRegex(ValueError, "belongs to data_mode=test"):
            self.service.get_learning_context(
                student_id="child-test", data_mode="real"
            )

    def test_summary_capture_cannot_masquerade_as_verbatim(self) -> None:
        items = self.sample_items()
        with self.assertRaisesRegex(ValueError, "source_quality='summary'"):
            self.service.record_assessment_run(
                student_id="child-test",
                data_mode="test",
                purpose="语音摘要",
                capture_mode="summary",
                items=items,
                idempotency_key="summary-001",
            )

    def test_focus_filters_recent_evidence(self) -> None:
        self.service.record_assessment_run(
            student_id="child-test",
            data_mode="test",
            purpose="does 后动词原形短验证",
            capture_mode="batch_verbatim",
            items=self.sample_items(),
            idempotency_key="focus-001",
        )
        context = self.service.get_learning_context(
            student_id="child-test", data_mode="test", focus="Jack", limit=10
        )
        self.assertEqual(len(context["recent_evidence"]), 1)
        self.assertIn("Jack", context["recent_evidence"][0]["prompt"])


if __name__ == "__main__":
    unittest.main()
