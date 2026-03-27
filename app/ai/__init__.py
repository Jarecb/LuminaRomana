"""AI integration layer."""

from app.ai.prompts import LessonPromptBuilder, PromptBuilder, SystemPromptBuilder
from app.ai.providers import BaseAIProvider, DisabledAIProvider, OpenAIChatProvider
from app.ai.service import AIService
from app.ai.types import (
    AIConfigurationError,
    AIError,
    AIMessage,
    AIProviderError,
    AIProviderResponse,
    LessonGenerationRequest,
    LessonGenerationError,
    LessonGenerationResult,
    PromptPackage,
    TransientAIError,
)

__all__ = [
    "AIConfigurationError",
    "AIError",
    "AIMessage",
    "AIProviderError",
    "AIProviderResponse",
    "AIService",
    "BaseAIProvider",
    "DisabledAIProvider",
    "LessonGenerationRequest",
    "LessonGenerationError",
    "LessonGenerationResult",
    "LessonPromptBuilder",
    "OpenAIChatProvider",
    "PromptBuilder",
    "PromptPackage",
    "SystemPromptBuilder",
    "TransientAIError",
]
