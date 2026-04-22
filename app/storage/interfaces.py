"""Storage interface protocols defining repository contracts.

Abstract repository Protocols used by the application so different storage backends
may be implemented without changing service logic.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.models import Lesson, Question, QuizAttempt, UserProgress, WordbankEntry, VerbbankEntry


class UserProgressRepository(Protocol):
    def get(self, user_id: str) -> UserProgress | None: ...

    def save(self, progress: UserProgress) -> None: ...

    def delete(self, user_id: str) -> None: ...


class LessonRepository(Protocol):
    def get(self, lesson_id: str) -> Lesson | None: ...

    def save(self, user_id: str, lesson: Lesson) -> None: ...

    def list_for_user(self, user_id: str, limit: int = 20) -> list[Lesson]: ...

    def delete_for_user(self, user_id: str) -> None: ...


class QuizAttemptRepository(Protocol):
    def save(self, attempt: QuizAttempt) -> None: ...

    def list_for_user(self, user_id: str, limit: int = 20) -> list[QuizAttempt]: ...

    def save_question_results(
        self,
        *,
        attempt: QuizAttempt,
        topic_id: str,
        results: Sequence[tuple[Question, bool]],
        track_outstanding: bool = True,
    ) -> None: ...

    def list_recent_correct_question_keys(
        self,
        user_id: str,
        *,
        recent_attempt_limit: int = 5,
    ) -> set[tuple[str, str, str, str]]: ...

    def list_recent_correct_question_prompts(
        self,
        user_id: str,
        *,
        recent_attempt_limit: int = 5,
        prompt_limit: int = 8,
    ) -> tuple[str, ...]: ...

    def list_pending_incorrect_questions(
        self,
        user_id: str,
        *,
        topic_id: str | None = None,
    ) -> list[Question]: ...

    def delete_for_user(self, user_id: str) -> None: ...


class WordbankRepository(Protocol):
    def upsert(self, entry: WordbankEntry) -> None: ...

    def search_for_user(self, user_id: str, query: str = "", limit: int = 100) -> list[WordbankEntry]: ...

    def delete_for_user(self, user_id: str) -> None: ...

    def update_definition(self, user_id: str, word: str, definition: str) -> None: ...


class VerbbankRepository(Protocol):
    def upsert(self, entry: VerbbankEntry) -> None: ...

    def search_for_user(self, user_id: str, query: str = "", limit: int = 100) -> list[VerbbankEntry]: ...

    def delete_for_user(self, user_id: str) -> None: ...

    def update_conjugations(self, user_id: str, verb: str, conjugations: str) -> None: ...


class OfflineQuestionRepository(Protocol):
    def upsert_questions(
        self,
        topic_id: str,
        questions: Sequence[Question],
        *,
        provider_name: str | None = None,
        model: str | None = None,
    ) -> int: ...

    def list_for_topic(self, topic_id: str, limit: int | None = None) -> list[Question]: ...

    def count_for_topic(self, topic_id: str) -> int: ...

    def count_all(self) -> int: ...

    def delete_all(self) -> int: ...
