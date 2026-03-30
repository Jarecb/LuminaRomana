from __future__ import annotations

from dataclasses import dataclass
import logging

# Added GeminiAIProvider to imports
from app.ai import AIService, DisabledAIProvider, AIChatProvider, GeminiAIProvider, PromptBuilder
from app.config import Settings
from app.logging_config import configure_logging
from app.services import ContentLibrary, DifficultyManager, QualityService
from app.services.learning import LearningService
from app.storage import (
    SQLiteLessonRepository,
    SQLiteQuizAttemptRepository,
    SQLiteStorage,
    SQLiteUserProgressRepository,
    SQLiteWordbankRepository,
)
from app.validation import ContentValidator


@dataclass(slots=True)
class Persistence:
    storage: SQLiteStorage
    user_progress: SQLiteUserProgressRepository
    lessons: SQLiteLessonRepository
    quiz_attempts: SQLiteQuizAttemptRepository
    wordbank: SQLiteWordbankRepository


@dataclass(slots=True)
class Application:
    settings: Settings
    logger: logging.Logger
    persistence: Persistence
    content_library: ContentLibrary
    difficulty_manager: DifficultyManager
    ai_service: AIService
    learning_service: LearningService
    quality_service: QualityService


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
        wordbank=SQLiteWordbankRepository(storage),
    )

    content_library = ContentLibrary()
    difficulty_manager = DifficultyManager(content_library)

    # --- FIXED AI PROVIDER LOGIC ---
    ai_settings = settings.ai
    provider = None

    if ai_settings.is_configured:
        if ai_settings.provider == "openai":
            provider = AIChatProvider(
                api_key=ai_settings.api_key or "",
                model=ai_settings.model,
                base_url=ai_settings.base_url,
                timeout_seconds=ai_settings.timeout_seconds,
            )
        elif ai_settings.provider == "google":
            provider = GeminiAIProvider(
                api_key=ai_settings.api_key or "",
                model=ai_settings.model,
                timeout_seconds=ai_settings.timeout_seconds,
            )

    # Fallback to disabled if configuration is missing or provider is unknown
    if provider is None:
        provider = DisabledAIProvider(
            provider_name=ai_settings.provider if ai_settings.enabled else "disabled",
            model=ai_settings.model,
        )

    # The AIService expects initialized Provider objects, not the raw Settings dataclass.
    ai_service = AIService(
        providers=[provider],  # CRITICAL FIX: Changed from [ai_settings] to [provider]
        prompt_builder=PromptBuilder(),
        content_library=content_library,
        difficulty_manager=difficulty_manager,
        content_validator=ContentValidator(),
        logger=logger.getChild("ai")
    )
    # -------------------------------

    learning_service = LearningService(
        user_progress_repository=persistence.user_progress,
        lesson_repository=persistence.lessons,
        quiz_attempt_repository=persistence.quiz_attempts,
        wordbank_repository=persistence.wordbank,
        content_library=content_library,
        difficulty_manager=difficulty_manager,
        ai_service=ai_service,
    )

    quality_service = QualityService(
        content_library=content_library,
        ai_service=ai_service,
    )

    return Application(
        settings=settings,
        logger=logger,
        persistence=persistence,
        content_library=content_library,
        difficulty_manager=difficulty_manager,
        ai_service=ai_service,
        learning_service=learning_service,
        quality_service=quality_service,
    )