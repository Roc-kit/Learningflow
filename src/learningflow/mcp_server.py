from __future__ import annotations

import os
from typing import Any, Literal

from mcp.server import MCPServer

from .runtime import service

mcp = MCPServer("Learningflow")


@mcp.tool()
def get_learning_context(
    student_id: str,
    data_mode: Literal["test", "real"],
    focus: str | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    """Read only the bounded learning evidence needed for the current teaching step.

    This M0 tool returns recent evidence and pending-review facts. It does not
    invent mastery scores and never exposes server-side answer keys or rubrics.
    """

    return service().get_learning_context(
        student_id=student_id,
        data_mode=data_mode,
        focus=focus,
        limit=limit,
    )


@mcp.tool()
def record_assessment_run(
    student_id: str,
    data_mode: Literal["test", "real"],
    purpose: str,
    capture_mode: Literal["live", "batch_verbatim", "summary"],
    items: list[dict[str, Any]],
    idempotency_key: str,
    session_id: str | None = None,
    surface: Literal["chatgpt", "web", "manual"] = "chatgpt",
) -> dict[str, Any]:
    """Persist one short, already-observed teaching/assessment episode.

    Prefer batch_verbatim for normal ChatGPT teaching so tool calls do not
    interrupt the learner. Each item should contain the actual prompt and
    actual learner response plus evidence provenance; assessment is optional.
    """

    return service().record_assessment_run(
        student_id=student_id,
        data_mode=data_mode,
        purpose=purpose,
        capture_mode=capture_mode,
        items=items,
        idempotency_key=idempotency_key,
        session_id=session_id,
        surface=surface,
    )


def main() -> None:
    """Run the Learningflow MCP server.

    stdio is the safest local default. Streamable HTTP is available for local
    integration testing; public deployment still requires a separate auth and
    transport-security pass before it is suitable for real student data.
    """

    transport = os.environ.get("LEARNINGFLOW_MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run()
        return
    if transport != "streamable-http":
        raise ValueError("LEARNINGFLOW_MCP_TRANSPORT must be stdio or streamable-http")

    host = os.environ.get("LEARNINGFLOW_MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("LEARNINGFLOW_MCP_PORT", "8000"))
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        json_response=True,
        stateless_http=True,
    )


if __name__ == "__main__":
    main()
