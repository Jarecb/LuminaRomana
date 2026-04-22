"""Dataclass types for the learning service surface area.

This keeps large DTOs out of the main service module so they can be imported individually where needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Dict

from app.models import Lesson, QuizAttempt, TopicMetadata, UserProgress, WordbankEntry, VerbbankEntry


@dataclass(frozen=True, slots=True)
class TopicAttemptSummary:
    topic_id: str
    attempts: int
    average_score: float
    latest_score: float | None
    page_passed: bool
    topic_passed: bool


@dataclass(frozen=True, slots=True)
class RoadmapProgressEntry:
    level: int
    topic_id: str
    title: str
    cefr_band: str
    mastery_percent: int
    status: str


@dataclass(frozen=True, slots=True)
class DashboardData:
    user_progress: UserProgress
    next_topic: TopicMetadata | None
    active_lesson: Lesson | None
    recommended_action: str
    recent_lessons: tuple[Lesson, ...]
    recent_attempts: tuple[QuizAttempt, ...]
    roadmap_entries: tuple[RoadmapProgressEntry, ...]
    current_topic_summary: TopicAttemptSummary | None
    pending_incorrect_count: int
    wordbank_size: int
    verbbank_size: int


@dataclass(frozen=True, slots=True)
class LevelIntro:
    topic: TopicMetadata
    principles: tuple[str, ...]
    summary: TopicAttemptSummary | None
    session_goal: str


@dataclass(frozen=True, slots=True)
class LevelRevision:
    topic: TopicMetadata
    vocabulary: tuple[tuple[str, str], ...]
    summary: TopicAttemptSummary | None
    session_goal: str


@dataclass(frozen=True, slots=True)
class LessonSession:
    page_kind: str
    topic: TopicMetadata
    session_goal: str
    resumed: bool
    source: str
    lesson: Lesson | None = None
    warnings: tuple[str, ...] = ()
    level_intro: LevelIntro | None = None
    level_revision: LevelRevision | None = None


@dataclass(frozen=True, slots=True)
class QuestionFeedback:
    question_id: str
    prompt: str
    correct_answer: str
    submitted_answer: str
    explanation: str
    why_wrong: str | None
    is_correct: bool
    tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QuizResult:
    lesson: Lesson
    score_percent: float
    average_score_percent: float
    correct_answers: int
    total_questions: int
    action: str
    next_topic: TopicMetadata | None
    topic_attempts: int
    topic_passed: bool
    pending_incorrect_count: int
    feedback: tuple[QuestionFeedback, ...]
    updated_progress: UserProgress


@dataclass(frozen=True, slots=True)
class WordbankData:
    query: str
    entries: tuple[WordbankEntry, ...]


@dataclass(frozen=True, slots=True)
class VerbbankData:
    query: str
    entries: tuple[VerbbankEntry, ...]


@dataclass(frozen=True, slots=True)
class PlacementOutcome:
    cefr_band: str
    suggested_level: int
    suggested_topic_id: str
    section_scores: dict[str, float]
    rationale: tuple[str, ...]
