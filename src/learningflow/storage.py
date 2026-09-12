from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS students (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    data_mode TEXT NOT NULL CHECK (data_mode IN ('test', 'real')),
    timezone TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learning_sessions (
    id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES students(id),
    source TEXT NOT NULL,
    intent TEXT,
    started_at TEXT NOT NULL,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS assessment_runs (
    id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES students(id),
    session_id TEXT NOT NULL REFERENCES learning_sessions(id),
    purpose TEXT NOT NULL,
    capture_mode TEXT NOT NULL CHECK (capture_mode IN ('live', 'batch_verbatim', 'summary')),
    surface TEXT NOT NULL CHECK (surface IN ('chatgpt', 'web', 'manual')),
    idempotency_key TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(student_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS assessment_items (
    id TEXT PRIMARY KEY,
    assessment_run_id TEXT NOT NULL REFERENCES assessment_runs(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    prompt TEXT NOT NULL,
    question_type TEXT,
    expected_answer TEXT,
    rubric_json TEXT,
    occurred_at TEXT,
    UNIQUE(assessment_run_id, position)
);

CREATE TABLE IF NOT EXISTS learner_responses (
    id TEXT PRIMARY KEY,
    assessment_item_id TEXT NOT NULL REFERENCES assessment_items(id) ON DELETE CASCADE,
    raw_answer TEXT NOT NULL,
    input_modality TEXT NOT NULL,
    source_quality TEXT NOT NULL,
    assistance_level TEXT NOT NULL,
    occurred_at TEXT,
    received_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assessment_revisions (
    id TEXT PRIMARY KEY,
    response_id TEXT NOT NULL REFERENCES learner_responses(id) ON DELETE CASCADE,
    result TEXT NOT NULL CHECK (
        result IN ('correct', 'incorrect', 'partial', 'unclear', 'pending_review')
    ),
    normalized_answer TEXT,
    reason TEXT,
    evaluation_method TEXT NOT NULL CHECK (
        evaluation_method IN ('deterministic', 'llm', 'human')
    ),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_assessment_runs_student_created
    ON assessment_runs(student_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_assessment_items_run
    ON assessment_items(assessment_run_id, position);
CREATE INDEX IF NOT EXISTS idx_responses_item
    ON learner_responses(assessment_item_id, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_assessment_revisions_response
    ON assessment_revisions(response_id, created_at DESC);
"""


class SQLiteStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def dumps(value: object | None) -> str | None:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
