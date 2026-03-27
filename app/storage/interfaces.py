from __future__ import annotations

from typing import Protocol

from app.models import Lesson, QuizAttempt, UserProgress


class UserProgressRepository(Protocol):
    def get(self, user_id: str) -> UserProgress | None: ...

    def save(self, progress: UserProgress) -> None: ...

    def delete(self, user_id: str) -> None: ...


class LessonRepository(Protocol):
    def get(self, lesson_id: str) -> Lesson | None: ...

    def save(self, user_id: str, lesson: Lesson) -> None: ...

    def list_for_user(self, user_id: str, limit: int = 20) -> list[Lesson]: ...


class QuizAttemptRepository(Protocol):
    def save(self, attempt: QuizAttempt) -> None: ...

    def list_for_user(self, user_id: str, limit: int = 20) -> list[QuizAttempt]: ...
