from __future__ import annotations

from dataclasses import dataclass
import logging

from app.config import Settings
from app.logging_config import configure_logging
from app.services import ContentLibrary, DifficultyManager
from app.storage import (
    SQLiteLessonRepository,
    SQLiteQuizAttemptRepository,
    SQLiteStorage,
    SQLiteUserProgressRepository,
)


@dataclass(slots=True)
class Persistence:
    storage: SQLiteStorage
    user_progress: SQLiteUserProgressRepository
    lessons: SQLiteLessonRepository
    quiz_attempts: SQLiteQuizAttemptRepository


@dataclass(slots=True)
class Application:
    settings: Settings
    logger: logging.Logger
    persistence: Persistence
    content_library: ContentLibrary
    difficulty_manager: DifficultyManager


def create_application() -> Application:
    settings = Settings.load()
    configure_logging(settings.log_level)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("lumina_romana")
    storage = SQLiteStorage(settings.database_path)
    storage.initialize()
    persistence = Persistence(
        storage=storage,
        user_progress=SQLiteUserProgressRepository(storage),
        lessons=SQLiteLessonRepository(storage),
        quiz_attempts=SQLiteQuizAttemptRepository(storage),
    )
    content_library = ContentLibrary()
    return Application(
        settings=settings,
        logger=logger,
        persistence=persistence,
        content_library=content_library,
        difficulty_manager=DifficultyManager(content_library),
    )
