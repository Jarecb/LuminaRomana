"""AI-related metrics and small constants."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AIServiceMetricsSnapshot:
    total_requests: int
    successful_generations: int
    fallback_generations: int
    validation_failures: int
    retries_attempted: int
    transient_failures: int
    provider_failures: int
    json_parse_failures: int


TEXT_LIMITS = {
    "explanation_text": 800,
    "example_sentence": 180,
    "question_prompt": 320,
    "question_explanation": 500,
}
