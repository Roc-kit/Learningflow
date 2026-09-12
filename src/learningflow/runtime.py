from __future__ import annotations

from functools import lru_cache

from .config import database_path
from .service import LearningService
from .storage import SQLiteStore


@lru_cache(maxsize=1)
def service() -> LearningService:
    return LearningService(SQLiteStore(database_path()))
