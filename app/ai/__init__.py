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
    "LessonGenerationResult",
    "LessonPromptBuilder",
    "OpenAIChatProvider",
    "PromptBuilder",
    "PromptPackage",
    "SystemPromptBuilder",
    "TransientAIError",
]
