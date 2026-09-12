from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from .storage import SQLiteStore

DataMode = Literal["test", "real"]
CaptureMode = Literal["live", "batch_verbatim", "summary"]
Surface = Literal["chatgpt", "web", "manual"]

VALID_INPUT_MODALITIES = {"text", "voice", "web", "other"}
VALID_SOURCE_QUALITIES = {
    "direct_text",
    "transcript",
    "model_interpretation",
    "summary",
    "server_captured",
}
VALID_ASSISTANCE_LEVELS = {"none", "light", "substantial", "unknown"}
VALID_RESULTS = {"correct", "incorrect", "partial", "unclear", "pending_review"}
VALID_EVALUATION_METHODS = {"deterministic", "llm", "human"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LearningService:
    """Small Stage 0 application service used by MCP and local maintenance."""

    def __init__(self, store: SQLiteStore):
        self.store = store

    def ensure_student(
        self,
        *,
        student_id: str,
        display_name: str,
        data_mode: DataMode,
        timezone_name: str = "Asia/Shanghai",
    ) -> dict[str, str]:
        student_id = student_id.strip()
        display_name = display_name.strip()
        if not student_id or not display_name:
            raise ValueError("student_id and display_name are required")
        self._require_data_mode(data_mode)

        with self.store.connect() as conn:
            existing = conn.execute(
                "SELECT * FROM students WHERE id = ?", (student_id,)
            ).fetchone()
            if existing:
                if existing["data_mode"] != data_mode:
                    raise ValueError(
                        f"student {student_id!r} already belongs to data_mode={existing['data_mode']}"
                    )
                return dict(existing)

            now = utc_now()
            conn.execute(
                """
                INSERT INTO students(id, display_name, data_mode, timezone, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (student_id, display_name, data_mode, timezone_name, now),
            )
            return {
                "id": student_id,
                "display_name": display_name,
                "data_mode": data_mode,
                "timezone": timezone_name,
                "created_at": now,
            }

    def get_learning_context(
        self,
        *,
        student_id: str,
        data_mode: DataMode,
        focus: str | None = None,
        limit: int = 8,
    ) -> dict[str, Any]:
        """Return a bounded, learner-safe context packet for ChatGPT.

        M0 deliberately returns evidence and pending review facts, not a
        fabricated mastery score or the server-side answer key/rubric.
        """

        self._require_data_mode(data_mode)
        if limit < 1 or limit > 20:
            raise ValueError("limit must be between 1 and 20")

        with self.store.connect() as conn:
            student = self._get_student(conn, student_id, data_mode)

            clauses = ["r.student_id = ?"]
            params: list[Any] = [student_id]
            if focus and focus.strip():
                needle = f"%{focus.strip()}%"
                clauses.append(
                    "(i.prompt LIKE ? OR a.reason LIKE ? OR lr.raw_answer LIKE ? OR r.purpose LIKE ?)"
                )
                params.extend([needle, needle, needle, needle])

            params.append(limit)
            rows = conn.execute(
                f"""
                SELECT
                    r.id AS assessment_run_id,
                    r.session_id,
                    r.purpose,
                    r.capture_mode,
                    r.surface,
                    r.created_at AS run_created_at,
                    i.id AS assessment_item_id,
                    i.position,
                    i.prompt,
                    i.question_type,
                    COALESCE(lr.raw_answer, '') AS raw_answer,
                    lr.input_modality,
                    lr.source_quality,
                    lr.assistance_level,
                    COALESCE(lr.occurred_at, lr.received_at) AS response_at,
                    a.result,
                    a.reason,
                    a.evaluation_method,
                    a.created_at AS assessed_at
                FROM assessment_runs r
                JOIN assessment_items i ON i.assessment_run_id = r.id
                LEFT JOIN learner_responses lr ON lr.id = (
                    SELECT lr2.id
                    FROM learner_responses lr2
                    WHERE lr2.assessment_item_id = i.id
                    ORDER BY lr2.received_at DESC
                    LIMIT 1
                )
                LEFT JOIN assessment_revisions a ON a.id = (
                    SELECT a2.id
                    FROM assessment_revisions a2
                    WHERE a2.response_id = lr.id
                    ORDER BY a2.created_at DESC
                    LIMIT 1
                )
                WHERE {' AND '.join(clauses)}
                ORDER BY COALESCE(lr.occurred_at, lr.received_at, r.created_at) DESC,
                         i.position DESC
                LIMIT ?
                """,
                params,
            ).fetchall()

        recent_evidence = [
            {
                "assessment_run_id": row["assessment_run_id"],
                "assessment_item_id": row["assessment_item_id"],
                "session_id": row["session_id"],
                "purpose": row["purpose"],
                "capture_mode": row["capture_mode"],
                "surface": row["surface"],
                "prompt": row["prompt"],
                "question_type": row["question_type"],
                "response": {
                    "raw_answer": row["raw_answer"],
                    "input_modality": row["input_modality"],
                    "source_quality": row["source_quality"],
                    "assistance_level": row["assistance_level"],
                    "occurred_at": row["response_at"],
                },
                "assessment": (
                    {
                        "result": row["result"],
                        "reason": row["reason"],
                        "evaluation_method": row["evaluation_method"],
                        "assessed_at": row["assessed_at"],
                    }
                    if row["result"]
                    else None
                ),
            }
            for row in rows
        ]

        return {
            "student": {
                "id": student["id"],
                "display_name": student["display_name"],
                "data_mode": student["data_mode"],
                "timezone": student["timezone"],
            },
            "focus": focus,
            "recent_evidence": recent_evidence,
            "pending_review": [
                evidence
                for evidence in recent_evidence
                if evidence["assessment"]
                and evidence["assessment"]["result"] in {"unclear", "pending_review"}
            ],
            "state_notice": "M0 returns evidence only; no learner mastery state is computed yet.",
        }

    def record_assessment_run(
        self,
        *,
        student_id: str,
        data_mode: DataMode,
        purpose: str,
        capture_mode: CaptureMode,
        items: list[dict[str, Any]],
        idempotency_key: str,
        session_id: str | None = None,
        surface: Surface = "chatgpt",
    ) -> dict[str, Any]:
        """Persist one short teaching/assessment episode as durable evidence."""

        self._require_data_mode(data_mode)
        if capture_mode not in {"live", "batch_verbatim", "summary"}:
            raise ValueError("invalid capture_mode")
        if surface not in {"chatgpt", "web", "manual"}:
            raise ValueError("invalid surface")
        purpose = purpose.strip()
        idempotency_key = idempotency_key.strip()
        if not purpose or not idempotency_key:
            raise ValueError("purpose and idempotency_key are required")
        if not items:
            raise ValueError("items must contain at least one question/response")
        if len(items) > 20:
            raise ValueError("M0 accepts at most 20 items per assessment run")

        validated_items = [
            self._validate_item(item, capture_mode=capture_mode) for item in items
        ]

        with self.store.connect() as conn:
            self._get_student(conn, student_id, data_mode)
            existing = conn.execute(
                """
                SELECT id, session_id, capture_mode
                FROM assessment_runs
                WHERE student_id = ? AND idempotency_key = ?
                """,
                (student_id, idempotency_key),
            ).fetchone()
            if existing:
                item_ids = [
                    row["id"]
                    for row in conn.execute(
                        """
                        SELECT id FROM assessment_items
                        WHERE assessment_run_id = ? ORDER BY position
                        """,
                        (existing["id"],),
                    ).fetchall()
                ]
                return {
                    "assessment_run_id": existing["id"],
                    "session_id": existing["session_id"],
                    "saved_item_ids": item_ids,
                    "capture_mode": existing["capture_mode"],
                    "warnings": ["idempotent_replay"],
                }

            resolved_session_id = self._resolve_session(
                conn,
                student_id=student_id,
                session_id=session_id,
                intent=purpose,
            )
            run_id = str(uuid4())
            now = utc_now()
            conn.execute(
                """
                INSERT INTO assessment_runs(
                    id, student_id, session_id, purpose, capture_mode,
                    surface, idempotency_key, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    student_id,
                    resolved_session_id,
                    purpose,
                    capture_mode,
                    surface,
                    idempotency_key,
                    now,
                ),
            )

            saved_item_ids: list[str] = []
            warnings: list[str] = []
            for position, item in enumerate(validated_items, start=1):
                item_id = str(uuid4())
                response_id = str(uuid4())
                saved_item_ids.append(item_id)
                conn.execute(
                    """
                    INSERT INTO assessment_items(
                        id, assessment_run_id, position, prompt, question_type,
                        expected_answer, rubric_json, occurred_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item_id,
                        run_id,
                        position,
                        item["prompt"],
                        item.get("question_type"),
                        item.get("expected_answer"),
                        self.store.dumps(item.get("rubric")),
                        item.get("occurred_at"),
                    ),
                )

                response = item["response"]
                conn.execute(
                    """
                    INSERT INTO learner_responses(
                        id, assessment_item_id, raw_answer, input_modality,
                        source_quality, assistance_level, occurred_at, received_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        response_id,
                        item_id,
                        response["raw_answer"],
                        response["input_modality"],
                        response["source_quality"],
                        response["assistance_level"],
                        item.get("occurred_at"),
                        now,
                    ),
                )

                assessment = item.get("assessment")
                if assessment:
                    conn.execute(
                        """
                        INSERT INTO assessment_revisions(
                            id, response_id, result, normalized_answer,
                            reason, evaluation_method, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid4()),
                            response_id,
                            assessment["result"],
                            assessment.get("normalized_answer"),
                            assessment.get("reason"),
                            assessment["evaluation_method"],
                            now,
                        ),
                    )
                else:
                    warnings.append(f"item_{position}_has_no_assessment")

            return {
                "assessment_run_id": run_id,
                "session_id": resolved_session_id,
                "saved_item_ids": saved_item_ids,
                "capture_mode": capture_mode,
                "warnings": warnings,
            }

    def _validate_item(
        self, item: dict[str, Any], *, capture_mode: CaptureMode
    ) -> dict[str, Any]:
        if not isinstance(item, dict):
            raise ValueError("each item must be an object")
        prompt = str(item.get("prompt") or "").strip()
        if not prompt:
            raise ValueError("each item requires prompt")

        response = item.get("response")
        if not isinstance(response, dict):
            raise ValueError("each item requires response")
        raw_answer = str(response.get("raw_answer") or "").strip()
        if not raw_answer:
            raise ValueError("response.raw_answer is required")
        input_modality = str(response.get("input_modality") or "")
        source_quality = str(response.get("source_quality") or "")
        assistance_level = str(response.get("assistance_level") or "")
        if input_modality not in VALID_INPUT_MODALITIES:
            raise ValueError(f"invalid input_modality: {input_modality}")
        if source_quality not in VALID_SOURCE_QUALITIES:
            raise ValueError(f"invalid source_quality: {source_quality}")
        if assistance_level not in VALID_ASSISTANCE_LEVELS:
            raise ValueError(f"invalid assistance_level: {assistance_level}")
        if capture_mode == "summary" and source_quality != "summary":
            raise ValueError(
                "summary capture_mode requires response.source_quality='summary'"
            )

        assessment = item.get("assessment")
        if assessment is not None:
            if not isinstance(assessment, dict):
                raise ValueError("assessment must be an object")
            result = str(assessment.get("result") or "")
            method = str(assessment.get("evaluation_method") or "")
            if result not in VALID_RESULTS:
                raise ValueError(f"invalid assessment result: {result}")
            if method not in VALID_EVALUATION_METHODS:
                raise ValueError(f"invalid evaluation_method: {method}")

        normalized = dict(item)
        normalized["prompt"] = prompt
        normalized["response"] = {
            **response,
            "raw_answer": raw_answer,
            "input_modality": input_modality,
            "source_quality": source_quality,
            "assistance_level": assistance_level,
        }
        return normalized

    def _resolve_session(
        self,
        conn: Any,
        *,
        student_id: str,
        session_id: str | None,
        intent: str,
    ) -> str:
        if session_id:
            row = conn.execute(
                "SELECT id, student_id, closed_at FROM learning_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if not row:
                raise ValueError(f"session not found: {session_id}")
            if row["student_id"] != student_id:
                raise ValueError("session belongs to another student")
            if row["closed_at"]:
                raise ValueError("session is already closed")
            return session_id

        new_session_id = str(uuid4())
        conn.execute(
            """
            INSERT INTO learning_sessions(id, student_id, source, intent, started_at)
            VALUES (?, ?, 'chatgpt', ?, ?)
            """,
            (new_session_id, student_id, intent, utc_now()),
        )
        return new_session_id

    @staticmethod
    def _require_data_mode(data_mode: str) -> None:
        if data_mode not in {"test", "real"}:
            raise ValueError("data_mode must be 'test' or 'real'")

    @staticmethod
    def _get_student(conn: Any, student_id: str, data_mode: DataMode) -> Any:
        row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        if not row:
            raise ValueError(f"student not found: {student_id}")
        if row["data_mode"] != data_mode:
            raise ValueError(
                f"student {student_id!r} belongs to data_mode={row['data_mode']}, not {data_mode}"
            )
        return row
