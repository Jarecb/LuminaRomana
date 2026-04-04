from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models import CEFRBand, Lesson, UserProgress


class AIError(Exception):
    """Base AI integration error."""


class AIConfigurationError(AIError):
    """Raised when AI generation is requested without a usable provider configuration."""


class AIProviderError(AIError):
    """Raised when the provider returns a non-recoverable error."""


class TransientAIError(AIProviderError):
    """Raised when a provider failure may succeed on retry."""


class QuotaExceededAIError(TransientAIError):
    """Raised when a provider rejects the request because quota has been exhausted."""

    def __init__(self, message: str, *, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class LessonGenerationError(AIError):
    """Raised when lesson generation cannot produce validated content."""


@dataclass(frozen=True, slots=True)
class AIMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class PromptPackage:
    messages: tuple[AIMessage, ...]
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class LessonGenerationRequest:
    user_progress: UserProgress
    topic_id: str
    session_goal: str = "lesson"
    focus_tags: tuple[str, ...] = ()
    question_count: int = 5
    temperature: float = 0.2
    strict_validation: bool = False
    validation_feedback: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AIProviderResponse:
    provider_name: str
    model: str
    content: str
    response_id: str | None = None
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class LessonGenerationResult:
    lesson: Lesson
    lesson_payload: dict[str, Any]
    provider_name: str
    model: str
    prompt: PromptPackage
    attempts: int
    source: str = "ai"
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class PromptContext:
    topic_id: str
    topic_title: str
    level: int
    cefr_band: CEFRBand
    difficulty: int
    session_goal: str
    recent_scores: tuple[float, ...]
    focus_tags: tuple[str, ...]
    blocked_topics: tuple[str, ...]
