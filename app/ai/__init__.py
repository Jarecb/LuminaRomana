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

# Explicitly define what is available for "from app.ai import *"
__all__ = [
    "AIService",
    "AIServiceMetricsSnapshot",
    "PromptBuilder",
    "BaseAIProvider",
    "AIChatProvider",
    "GeminiAIProvider",
    "DisabledAIProvider",
]