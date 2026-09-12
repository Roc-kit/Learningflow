from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    configured = os.environ.get("LEARNINGFLOW_DATA_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path("data")


def database_path() -> Path:
    """Return the Stage 0 SQLite database path.

    The local SQLite file is intentionally a development/runtime detail. The
    domain service does not expose SQLite concepts to ChatGPT or to callers.
    """

    configured = os.environ.get("LEARNINGFLOW_DB_PATH")
    if configured:
        return Path(configured).expanduser()
    return data_dir() / "learningflow.db"
