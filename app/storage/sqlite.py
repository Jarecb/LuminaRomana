from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Iterator

from app.models import CEFRBand, ExampleSentence, Lesson, Question, QuestionType, QuizAttempt, UserProgress


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _deserialize_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def _lesson_to_record(lesson: Lesson) -> str:
    payload = {
        "lesson_id": lesson.lesson_id,
        "topic": lesson.topic,
        "level": lesson.level,
        "cefr_band": lesson.cefr_band.value,
        "difficulty": lesson.difficulty,
        "explanation_text": lesson.explanation_text,
        "example_sentences": [
            {"romanian": sentence.romanian, "english": sentence.english}
            for sentence in lesson.example_sentences
        ],
        "key_rules": lesson.key_rules,
        "quiz_questions": [
            {
                "question_id": question.question_id,
                "prompt": question.prompt,
                "question_type": question.question_type.value,
                "difficulty_rating": question.difficulty_rating,
                "cefr_band": question.cefr_band.value,
                "correct_answer": question.correct_answer,
                "explanation": question.explanation,
                "tags": question.tags,
                "options": question.options,
                "hint": question.hint,
                "rubric": question.rubric,
            }
            for question in lesson.quiz_questions
        ],
        "created_at": _serialize_datetime(lesson.created_at),
    }
    return json.dumps(payload, ensure_ascii=False)


def _lesson_from_record(payload: str) -> Lesson:
    raw = json.loads(payload)
    return Lesson(
        lesson_id=raw["lesson_id"],
        topic=raw["topic"],
        level=raw["level"],
        cefr_band=CEFRBand(raw["cefr_band"]),
        difficulty=raw["difficulty"],
        explanation_text=raw["explanation_text"],
        example_sentences=[
            ExampleSentence(romanian=sentence["romanian"], english=sentence["english"])
            for sentence in raw["example_sentences"]
        ],
        key_rules=list(raw["key_rules"]),
        quiz_questions=[
            Question(
                question_id=question["question_id"],
                prompt=question["prompt"],
                question_type=QuestionType(question["question_type"]),
                difficulty_rating=question["difficulty_rating"],
                cefr_band=CEFRBand(question["cefr_band"]),
                correct_answer=question["correct_answer"],
                explanation=question["explanation"],
                tags=list(question["tags"]),
                options=list(question["options"]),
                hint=question["hint"],
                rubric=dict(question["rubric"]),
            )
            for question in raw["quiz_questions"]
        ],
        created_at=_deserialize_datetime(raw["created_at"]) or datetime.now(),
    )


@dataclass(slots=True)
class SQLiteStorage:
    database_path: Path

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    current_level INTEGER NOT NULL,
                    current_cefr_band TEXT NOT NULL,
                    current_difficulty INTEGER NOT NULL,
                    total_xp INTEGER NOT NULL,
                    recent_scores TEXT NOT NULL,
                    last_lesson_date TEXT
                );

                CREATE TABLE IF NOT EXISTS topic_mastery (
                    user_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    proficiency_score REAL NOT NULL,
                    PRIMARY KEY (user_id, topic),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS skill_scores (
                    user_id TEXT NOT NULL,
                    skill_name TEXT NOT NULL,
                    score REAL NOT NULL,
                    PRIMARY KEY (user_id, skill_name),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS lesson_history (
                    lesson_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    difficulty INTEGER NOT NULL,
                    cefr_band TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS quiz_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    lesson_id TEXT NOT NULL,
                    score_percent REAL NOT NULL,
                    mistake_tags TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (lesson_id) REFERENCES lesson_history(lesson_id) ON DELETE CASCADE
                );
                """
            )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


@dataclass(slots=True)
class SQLiteUserProgressRepository:
    storage: SQLiteStorage

    def get(self, user_id: str) -> UserProgress | None:
        with self.storage.connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if row is None:
                return None

            mastery_rows = conn.execute(
                "SELECT topic, proficiency_score FROM topic_mastery WHERE user_id = ?",
                (user_id,),
            ).fetchall()
            skill_rows = conn.execute(
                "SELECT skill_name, score FROM skill_scores WHERE user_id = ?",
                (user_id,),
            ).fetchall()

        return UserProgress(
            user_id=row["id"],
            current_level=row["current_level"],
            current_cefr_band=CEFRBand(row["current_cefr_band"]),
            current_difficulty=row["current_difficulty"],
            total_xp=row["total_xp"],
            mastery_matrix={entry["topic"]: entry["proficiency_score"] for entry in mastery_rows},
            recent_scores=list(json.loads(row["recent_scores"])),
            skill_scores={entry["skill_name"]: entry["score"] for entry in skill_rows},
            last_lesson_at=_deserialize_datetime(row["last_lesson_date"]),
        )

    def save(self, progress: UserProgress) -> None:
        with self.storage.connection() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    id, current_level, current_cefr_band, current_difficulty,
                    total_xp, recent_scores, last_lesson_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    current_level = excluded.current_level,
                    current_cefr_band = excluded.current_cefr_band,
                    current_difficulty = excluded.current_difficulty,
                    total_xp = excluded.total_xp,
                    recent_scores = excluded.recent_scores,
                    last_lesson_date = excluded.last_lesson_date
                """,
                (
                    progress.user_id,
                    progress.current_level,
                    progress.current_cefr_band.value,
                    progress.current_difficulty,
                    progress.total_xp,
                    json.dumps(progress.recent_scores),
                    _serialize_datetime(progress.last_lesson_at),
                ),
            )

            conn.execute("DELETE FROM topic_mastery WHERE user_id = ?", (progress.user_id,))
            conn.executemany(
                """
                INSERT INTO topic_mastery (user_id, topic, proficiency_score)
                VALUES (?, ?, ?)
                """,
                [
                    (progress.user_id, topic, score)
                    for topic, score in sorted(progress.mastery_matrix.items())
                ],
            )

            conn.execute("DELETE FROM skill_scores WHERE user_id = ?", (progress.user_id,))
            conn.executemany(
                """
                INSERT INTO skill_scores (user_id, skill_name, score)
                VALUES (?, ?, ?)
                """,
                [
                    (progress.user_id, skill, score)
                    for skill, score in sorted(progress.skill_scores.items())
                ],
            )

    def delete(self, user_id: str) -> None:
        with self.storage.connection() as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


@dataclass(slots=True)
class SQLiteLessonRepository:
    storage: SQLiteStorage

    def get(self, lesson_id: str) -> Lesson | None:
        with self.storage.connection() as conn:
            row = conn.execute(
                "SELECT payload FROM lesson_history WHERE lesson_id = ?",
                (lesson_id,),
            ).fetchone()
        return _lesson_from_record(row["payload"]) if row is not None else None

    def save(self, user_id: str, lesson: Lesson) -> None:
        with self.storage.connection() as conn:
            conn.execute(
                """
                INSERT INTO lesson_history (
                    lesson_id, user_id, topic, level, difficulty, cefr_band, created_at, payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(lesson_id) DO UPDATE SET
                    user_id = excluded.user_id,
                    topic = excluded.topic,
                    level = excluded.level,
                    difficulty = excluded.difficulty,
                    cefr_band = excluded.cefr_band,
                    created_at = excluded.created_at,
                    payload = excluded.payload
                """,
                (
                    lesson.lesson_id,
                    user_id,
                    lesson.topic,
                    lesson.level,
                    lesson.difficulty,
                    lesson.cefr_band.value,
                    _serialize_datetime(lesson.created_at),
                    _lesson_to_record(lesson),
                ),
            )

    def list_for_user(self, user_id: str, limit: int = 20) -> list[Lesson]:
        with self.storage.connection() as conn:
            rows = conn.execute(
                """
                SELECT payload
                FROM lesson_history
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [_lesson_from_record(row["payload"]) for row in rows]


@dataclass(slots=True)
class SQLiteQuizAttemptRepository:
    storage: SQLiteStorage

    def save(self, attempt: QuizAttempt) -> None:
        with self.storage.connection() as conn:
            conn.execute(
                """
                INSERT INTO quiz_attempts (
                    attempt_id, user_id, lesson_id, score_percent, mistake_tags, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(attempt_id) DO UPDATE SET
                    user_id = excluded.user_id,
                    lesson_id = excluded.lesson_id,
                    score_percent = excluded.score_percent,
                    mistake_tags = excluded.mistake_tags,
                    created_at = excluded.created_at
                """,
                (
                    attempt.attempt_id,
                    attempt.user_id,
                    attempt.lesson_id,
                    attempt.score_percent,
                    json.dumps(attempt.mistake_tags),
                    _serialize_datetime(attempt.created_at),
                ),
            )

    def list_for_user(self, user_id: str, limit: int = 20) -> list[QuizAttempt]:
        with self.storage.connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM quiz_attempts
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

        return [
            QuizAttempt(
                attempt_id=row["attempt_id"],
                user_id=row["user_id"],
                lesson_id=row["lesson_id"],
                score_percent=row["score_percent"],
                mistake_tags=list(json.loads(row["mistake_tags"])),
                created_at=_deserialize_datetime(row["created_at"]) or datetime.now(),
            )
            for row in rows
        ]
