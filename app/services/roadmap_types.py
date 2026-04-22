"""Types for roadmap fallback templates.

Keeps the fallback template dataclasses in a small module to reduce roadmap.py size.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from app.models import QuestionType, ExampleSentence


@dataclass(frozen=True, slots=True)
class FallbackQuestionTemplate:
    prompt: str
    question_type: QuestionType
    correct_answer: str
    explanation: str
    tags: tuple[str, ...]
    options: tuple[str, ...] = ()
    hint: str | None = None
    rubric: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class FallbackLessonTemplate:
    explanation_text: str
    key_rules: tuple[str, ...]
    example_sentences: tuple[ExampleSentence, ...]
    questions: tuple[FallbackQuestionTemplate, ...]
