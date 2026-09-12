from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from learningflow import runtime
from learningflow.mcp_server import mcp


class MCPToolsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("LEARNINGFLOW_DB_PATH")
        os.environ["LEARNINGFLOW_DB_PATH"] = str(Path(self.tmp.name) / "mcp.db")
        runtime.service.cache_clear()
        runtime.service().ensure_student(
            student_id="mcp-test-child",
            display_name="MCP 测试学生",
            data_mode="test",
        )

    async def asyncTearDown(self) -> None:
        runtime.service.cache_clear()
        if self.previous_db_path is None:
            os.environ.pop("LEARNINGFLOW_DB_PATH", None)
        else:
            os.environ["LEARNINGFLOW_DB_PATH"] = self.previous_db_path
        self.tmp.cleanup()

    async def test_server_exposes_only_stage0_core_tools(self) -> None:
        tools = await mcp.list_tools()
        self.assertEqual(
            [tool.name for tool in tools],
            ["get_learning_context", "record_assessment_run"],
        )

    async def test_tools_round_trip_evidence(self) -> None:
        write = await mcp.call_tool(
            "record_assessment_run",
            {
                "student_id": "mcp-test-child",
                "data_mode": "test",
                "purpose": "MCP 自动测试",
                "capture_mode": "batch_verbatim",
                "idempotency_key": "mcp-auto-001",
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
            },
        )
        self.assertEqual(write.structured_content["warnings"], [])

        read = await mcp.call_tool(
            "get_learning_context",
            {"student_id": "mcp-test-child", "data_mode": "test"},
        )
        evidence = read.structured_content["recent_evidence"]
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["response"]["raw_answer"], "like")
        self.assertEqual(evidence[0]["assessment"]["result"], "correct")


if __name__ == "__main__":
    unittest.main()
