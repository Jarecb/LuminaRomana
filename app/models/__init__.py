"""Public model exports for Lumina Romana.

Re-exports core domain dataclasses and roadmap metadata for convenient imports
through app.models.
"""
from app.models.domain import CEFRBand, ExampleSentence, Lesson, Question, QuestionType, QuizAttempt, UserProgress, WordbankEntry, VerbbankEntry
from app.models.roadmap import PLACEMENT_TEST_BLUEPRINT, PlacementTestSection, ROADMAP_TOPICS, TopicMetadata

__all__ = [
    "CEFRBand",
    "ExampleSentence",
    "Lesson",
    "PLACEMENT_TEST_BLUEPRINT",
    "PlacementTestSection",
    "Question",
    "QuestionType",
    "QuizAttempt",
    "ROADMAP_TOPICS",
    "TopicMetadata",
    "UserProgress",
    "WordbankEntry",
    "VerbbankEntry",
]
