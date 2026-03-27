from __future__ import annotations

from dataclasses import dataclass
import logging

from app.ai import AIService, DisabledAIProvider, OpenAIChatProvider, PromptBuilder
from app.config import Settings
from app.logging_config import configure_logging
from app.services import ContentLibrary, DifficultyManager
from app.storage import (
    SQLiteLessonRepository,
    SQLiteQuizAttemptRepository,
    SQLiteStorage,
    SQLiteUserProgressRepository,
)
from app.validation import ContentValidator


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
    ai_service: AIService


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
    difficulty_manager = DifficultyManager(content_library)
    ai_settings = settings.ai
    if ai_settings.provider == "openai" and ai_settings.configured:
        provider = OpenAIChatProvider(
            api_key=ai_settings.api_key or "",
            model=ai_settings.model,
            base_url=ai_settings.base_url,
            timeout_seconds=ai_settings.timeout_seconds,
        )
    elif not ai_settings.enabled or not ai_settings.api_key:
        provider = DisabledAIProvider(
            provider_name=ai_settings.provider if ai_settings.enabled else "disabled",
            model=ai_settings.model,
        )
    else:
        raise ValueError(f"Unsupported AI provider '{ai_settings.provider}'.")
    return Application(
        settings=settings,
        logger=logger,
        persistence=persistence,
        content_library=content_library,
        difficulty_manager=difficulty_manager,
        ai_service=AIService(
            provider=provider,
            prompt_builder=PromptBuilder(),
            content_library=content_library,
            difficulty_manager=difficulty_manager,
            content_validator=ContentValidator(),
            logger=logger.getChild("ai"),
            max_retries=ai_settings.max_retries,
        ),
    )
