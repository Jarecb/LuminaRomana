"""Core domain models and simple validation for learner state and questions.

Defines dataclasses for questions, lessons, quiz attempts, vocabulary entries, and
user progress with lightweight validation performed in __post_init__ hooks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CEFRBand(StrEnum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"


class QuestionType(StrEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    ENGLISH_TO_ROMANIAN = "english_to_romanian_translation"
    ROMANIAN_TO_ENGLISH = "romanian_to_english_translation"
    FILL_IN_THE_BLANK = "fill_in_the_blank"
    ERROR_IDENTIFICATION = "grammar_error_identification"
    SENTENCE_TRANSFORMATION = "sentence_transformation"
    GUIDED_WRITING = "guided_writing"
    READING_COMPREHENSION = "reading_comprehension"
    DIALOGUE_COMPLETION = "dialogue_completion"


@dataclass(slots=True)
class ExampleSentence:
    romanian: str
    english: str


@dataclass(slots=True)
class Question:
    question_id: str
    prompt: str
    question_type: QuestionType
    difficulty_rating: int
    cefr_band: CEFRBand
    correct_answer: str
    explanation: str
    tags: list[str]
    options: list[str] = field(default_factory=list)
    hint: str | None = None
    rubric: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 1 <= self.difficulty_rating <= 10:
            raise ValueError("Question difficulty must be between 1 and 10.")
        if not self.explanation.strip():
            raise ValueError("Question explanation cannot be empty.")
        if self.options and self.correct_answer not in self.options:
            raise ValueError("Question correct answer must appear in options.")


@dataclass(slots=True)
class Lesson:
    lesson_id: str
    topic: str
    level: int
    cefr_band: CEFRBand
    difficulty: int
    explanation_text: str
    example_sentences: list[ExampleSentence]
    key_rules: list[str]
    quiz_questions: list[Question]
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.level < 1:
            raise ValueError("Lesson level must be at least 1.")
        if not 1 <= self.difficulty <= 10:
            raise ValueError("Lesson difficulty must be between 1 and 10.")
        if not self.explanation_text.strip():
            raise ValueError("Lesson explanation text cannot be empty.")


@dataclass(slots=True)
class QuizAttempt:
    attempt_id: str
    user_id: str
    lesson_id: str
    score_percent: float
    mistake_tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not 0.0 <= self.score_percent <= 100.0:
            raise ValueError("Quiz attempt score must be between 0 and 100.")


@dataclass(slots=True)
class WordbankEntry:
    user_id: str
    word: str
    definition: str
    topic: str
    example_usage: str = ""
    first_seen_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.word.strip():
            raise ValueError("Wordbank entries require a word.")
        if not self.definition.strip():
            raise ValueError("Wordbank entries require a definition.")
        if not self.topic.strip():
            raise ValueError("Wordbank entries require a topic.")


@dataclass(slots=True)
class VerbbankEntry:
    user_id: str
    verb: str
    conjugations: str
    topic: str
    translation: str = ""
    first_seen_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.verb.strip():
            raise ValueError("Verbbank entries require a verb.")
        if not self.conjugations.strip():
            raise ValueError("Verbbank entries require conjugations.")
        if not self.topic.strip():
            raise ValueError("Verbbank entries require a topic.")


@dataclass(slots=True)
class UserProgress:
    user_id: str
    current_level: int = 1
    current_cefr_band: CEFRBand = CEFRBand.A1
    current_difficulty: int = 1
    total_xp: int = 0
    mastery_matrix: dict[str, float] = field(default_factory=dict)
    recent_scores: list[float] = field(default_factory=list)
    skill_scores: dict[str, float] = field(default_factory=dict)
    last_lesson_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.current_level < 1:
            raise ValueError("Current level must be at least 1.")
        if not 1 <= self.current_difficulty <= 10:
            raise ValueError("Current difficulty must be between 1 and 10.")
        if self.total_xp < 0:
            raise ValueError("Total XP cannot be negative.")

    def update_mastery(self, topic: str, proficiency_score: float) -> None:
        if not 0.0 <= proficiency_score <= 1.0:
            raise ValueError("Mastery scores must be between 0.0 and 1.0.")
        self.mastery_matrix[topic] = proficiency_score

    def update_skill_score(self, skill_name: str, score: float) -> None:
        if not 0.0 <= score <= 100.0:
            raise ValueError("Skill scores must be between 0 and 100.")
        self.skill_scores[skill_name] = score

    def record_quiz_attempt(self, score_percent: float, completed_at: datetime | None = None) -> None:
        if not 0.0 <= score_percent <= 100.0:
            raise ValueError("Quiz scores must be between 0 and 100.")
        self.recent_scores = [*self.recent_scores[-2:], score_percent]
        self.total_xp += int(round(score_percent))
        self.last_lesson_at = completed_at or utc_now()
