"""Application bootstrap and dependency wiring.

Creates the Settings, storage layer, repositories, services, and AI provider wiring
used to instantiate the running application object.
"""
from __future__ import annotations

from dataclasses import dataclass
import logging

from app.ai import AIService, DisabledAIProvider, AIChatProvider, GeminiAIProvider, PromptBuilder
from app.config import Settings
from app.logging_config import configure_logging
from app.services import ContentLibrary, DifficultyManager, QualityService
from app.services.learning import LearningService
from app.storage import (
    SQLiteLessonRepository,
    SQLiteOfflineQuestionRepository,
    SQLiteQuizAttemptRepository,
    SQLiteStorage,
    SQLiteUserProgressRepository,
    SQLiteWordbankRepository,
    SQLiteVerbbankRepository,
)
from app.validation import ContentValidator


@dataclass(slots=True)
class Persistence:
    storage: SQLiteStorage
    user_progress: SQLiteUserProgressRepository
    lessons: SQLiteLessonRepository
    offline_questions: SQLiteOfflineQuestionRepository
    quiz_attempts: SQLiteQuizAttemptRepository
    wordbank: SQLiteWordbankRepository
    verbbank: SQLiteVerbbankRepository


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


def create_application(*, offline_only: bool = False) -> Application:
    settings = Settings.load(offline_only=offline_only)
    configure_logging(settings.log_level)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("lumina_romana")

    storage = SQLiteStorage(settings.database_path)
    storage.initialize()

    persistence = Persistence(
        storage=storage,
        user_progress=SQLiteUserProgressRepository(storage),
        lessons=SQLiteLessonRepository(storage),
        offline_questions=SQLiteOfflineQuestionRepository(storage),
        quiz_attempts=SQLiteQuizAttemptRepository(storage),
        wordbank=SQLiteWordbankRepository(storage),
        verbbank=SQLiteVerbbankRepository(storage),
    )

    content_library = ContentLibrary(offline_question_repository=persistence.offline_questions)
    difficulty_manager = DifficultyManager(content_library)

    ai_settings = settings.ai
    provider = _build_ai_provider(ai_settings)

    ai_service = AIService(
        providers=[provider],
        prompt_builder=PromptBuilder(),
        content_library=content_library,
        difficulty_manager=difficulty_manager,
        content_validator=ContentValidator(),
        logger=logger.getChild("ai"),
        max_retries_per_provider=ai_settings.max_retries,
        offline_question_repository=persistence.offline_questions,
    )

    learning_service = LearningService(
        user_progress_repository=persistence.user_progress,
        lesson_repository=persistence.lessons,
        quiz_attempt_repository=persistence.quiz_attempts,
        wordbank_repository=persistence.wordbank,
        verbbank_repository=persistence.verbbank,
        content_library=content_library,
        difficulty_manager=difficulty_manager,
        ai_service=ai_service,
    )

    quality_service = QualityService(
        content_library=content_library,
        ai_service=ai_service,
        offline_question_repository=persistence.offline_questions,
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


def _build_ai_provider(ai_settings) -> DisabledAIProvider | AIChatProvider | GeminiAIProvider:
    if ai_settings.offline_only:
        return DisabledAIProvider(
            provider_name="offline",
            model="offline-only",
        )

    normalized_provider = ai_settings.provider.strip().lower()
    if not ai_settings.is_configured:
        return DisabledAIProvider(
            provider_name=normalized_provider if ai_settings.enabled else "disabled",
            model=ai_settings.model,
        )

    if normalized_provider in {"openai", "copilot", "github", "github_models"}:
        provider_name = "copilot" if normalized_provider != "openai" else "openai"
        return AIChatProvider(
            api_key=ai_settings.api_key or "",
            model=ai_settings.model,
            base_url=ai_settings.base_url,
            provider_name=provider_name,
            timeout_seconds=ai_settings.timeout_seconds,
        )

    if normalized_provider in {"google", "gemini"}:
        return GeminiAIProvider(
            api_key=ai_settings.api_key or "",
            model=ai_settings.model,
            provider_name="gemini",
            timeout_seconds=ai_settings.timeout_seconds,
        )

    return DisabledAIProvider(
        provider_name=normalized_provider or "disabled",
        model=ai_settings.model,
    )
