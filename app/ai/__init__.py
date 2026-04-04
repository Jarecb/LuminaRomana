from __future__ import annotations

# Import from the service module
from app.ai.service import AIService, AIServiceMetricsSnapshot

# Import from the prompts module
from app.ai.prompts import PromptBuilder

# Import the providers from the providers module
from app.ai.providers import (
    BaseAIProvider,
    AIChatProvider,
    GeminiAIProvider,  # This was likely missing
    DisabledAIProvider,
)
from app.ai.types import (
    AIConfigurationError,
    AIMessage,
    AIProviderError,
    AIProviderResponse,
    LessonGenerationError,
    LessonGenerationRequest,
    LessonGenerationResult,
    PromptContext,
    PromptPackage,
    QuotaExceededAIError,
    TransientAIError,
)

# Explicitly define what is available for "from app.ai import *"
__all__ = [
    "AIService",
    "AIServiceMetricsSnapshot",
    "AIConfigurationError",
    "AIMessage",
    "AIProviderError",
    "AIProviderResponse",
    "PromptBuilder",
    "PromptContext",
    "PromptPackage",
    "BaseAIProvider",
    "AIChatProvider",
    "GeminiAIProvider",
    "DisabledAIProvider",
    "LessonGenerationError",
    "LessonGenerationRequest",
    "LessonGenerationResult",
    "QuotaExceededAIError",
    "TransientAIError",
]
