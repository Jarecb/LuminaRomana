"""SQLite-backed storage layer and repository implementations.

Provides SQLiteStorage and repository classes that serialize domain models to JSON
and persist them into a local SQLite database used by the application.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from collections.abc import Sequence
from typing import Iterator

from app.models import CEFRBand, ExampleSentence, Lesson, Question, QuestionType, QuizAttempt, UserProgress, WordbankEntry, VerbbankEntry


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


def _question_to_record(question: Question) -> str:
    payload = {
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
    return json.dumps(payload, ensure_ascii=False)


def _question_from_record(payload: str) -> Question:
    raw = json.loads(payload)
    return Question(
        question_id=raw["question_id"],
        prompt=raw["prompt"],
        question_type=QuestionType(raw["question_type"]),
        difficulty_rating=raw["difficulty_rating"],
        cefr_band=CEFRBand(raw["cefr_band"]),
        correct_answer=raw["correct_answer"],
        explanation=raw["explanation"],
        tags=list(raw["tags"]),
        options=list(raw["options"]),
        hint=raw["hint"],
        rubric=dict(raw["rubric"]),
    )


def _question_fingerprint(topic_id: str, question: Question) -> str:
    payload = {
        "topic": topic_id,
        "prompt": question.prompt.strip(),
        "question_type": question.question_type.value,
        "correct_answer": question.correct_answer.strip(),
        "explanation": question.explanation.strip(),
        "tags": sorted(question.tags),
        "options": question.options,
        "hint": question.hint,
        "rubric": question.rubric,
        "cefr_band": question.cefr_band.value,
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _question_cooldown_key(topic_id: str, question: Question) -> tuple[str, str, str, str]:
    return (
        topic_id,
        question.question_type.value,
        question.prompt.strip().casefold(),
        question.correct_answer.strip().casefold(),
    )


def _question_history_key(topic_id: str, question: Question) -> str:
    serialized = json.dumps(
        _question_cooldown_key(topic_id, question),
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


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

                CREATE TABLE IF NOT EXISTS quiz_question_results (
                    attempt_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    question_type TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    is_correct INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (attempt_id, topic, question_type, prompt, correct_answer),
                    FOREIGN KEY (attempt_id) REFERENCES quiz_attempts(attempt_id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS pending_incorrect_questions (
                    user_id TEXT NOT NULL,
                    question_key TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    question_type TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    first_incorrect_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, question_key),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS wordbank (
                    user_id TEXT NOT NULL,
                    word TEXT NOT NULL,
                    definition TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, word),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS verbbank (
                    user_id TEXT NOT NULL,
                    verb TEXT NOT NULL,
                    conjugations TEXT NOT NULL,
                    translation TEXT NOT NULL DEFAULT '',
                    topic TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, verb),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS offline_question_bank (
                    fingerprint TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    question_type TEXT NOT NULL,
                    difficulty_rating INTEGER NOT NULL,
                    cefr_band TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    options TEXT NOT NULL,
                    hint TEXT,
                    rubric TEXT NOT NULL,
                    provider_name TEXT,
                    model TEXT,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );
                """
            )
            self._ensure_column(conn, "verbbank", "translation", "TEXT NOT NULL DEFAULT ''")

    def _ensure_column(self, conn: sqlite3.Connection, table_name: str, column_name: str, column_sql: str) -> None:
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})")}
        if column_name in columns:
            return
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")

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

    def delete_for_user(self, user_id: str) -> None:
        with self.storage.connection() as conn:
            conn.execute("DELETE FROM lesson_history WHERE user_id = ?", (user_id,))


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

    def save_question_results(
        self,
        *,
        attempt: QuizAttempt,
        topic_id: str,
        results: Sequence[tuple[Question, bool]],
        track_outstanding: bool = True,
    ) -> None:
        timestamp = _serialize_datetime(attempt.created_at) or datetime.now().isoformat()
        rows = [
            (
                attempt.attempt_id,
                attempt.user_id,
                topic_id,
                question.question_type.value,
                question.prompt,
                question.correct_answer,
                int(is_correct),
                timestamp,
            )
            for question, is_correct in results
        ]
        if not rows:
            return

        with self.storage.connection() as conn:
            conn.executemany(
                """
                INSERT INTO quiz_question_results (
                    attempt_id, user_id, topic, question_type, prompt, correct_answer, is_correct, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(attempt_id, topic, question_type, prompt, correct_answer) DO UPDATE SET
                    is_correct = excluded.is_correct,
                    created_at = excluded.created_at
                """,
                rows,
            )
            if not track_outstanding:
                return

            resolved_rows: list[tuple[str, str]] = []
            pending_rows: list[tuple[str, str, str, str, str, str, str, str, str]] = []
            for question, is_correct in results:
                question_key = _question_history_key(topic_id, question)
                if is_correct:
                    resolved_rows.append((attempt.user_id, question_key))
                    continue
                pending_rows.append(
                    (
                        attempt.user_id,
                        question_key,
                        topic_id,
                        question.question_type.value,
                        question.prompt,
                        question.correct_answer,
                        _question_to_record(question),
                        timestamp,
                        timestamp,
                    )
                )

            if resolved_rows:
                conn.executemany(
                    """
                    DELETE FROM pending_incorrect_questions
                    WHERE user_id = ? AND question_key = ?
                    """,
                    resolved_rows,
                )

            if pending_rows:
                conn.executemany(
                    """
                    INSERT INTO pending_incorrect_questions (
                        user_id, question_key, topic, question_type, prompt, correct_answer,
                        payload, first_incorrect_at, last_seen_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, question_key) DO UPDATE SET
                        topic = excluded.topic,
                        question_type = excluded.question_type,
                        prompt = excluded.prompt,
                        correct_answer = excluded.correct_answer,
                        payload = excluded.payload,
                        last_seen_at = excluded.last_seen_at
                    """,
                    pending_rows,
                )

    def list_recent_correct_question_keys(
        self,
        user_id: str,
        *,
        recent_attempt_limit: int = 5,
    ) -> set[tuple[str, str, str, str]]:
        with self.storage.connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT qqr.topic, qqr.question_type, qqr.prompt, qqr.correct_answer
                FROM quiz_question_results AS qqr
                WHERE qqr.user_id = ?
                  AND qqr.is_correct = 1
                  AND qqr.attempt_id IN (
                      SELECT attempt_id
                      FROM quiz_attempts
                      WHERE user_id = ?
                      ORDER BY created_at DESC
                      LIMIT ?
                  )
                """,
                (user_id, user_id, recent_attempt_limit),
            ).fetchall()

        return {
            (
                row["topic"],
                row["question_type"],
                row["prompt"].strip().casefold(),
                row["correct_answer"].strip().casefold(),
            )
            for row in rows
        }

    def list_recent_correct_question_prompts(
        self,
        user_id: str,
        *,
        recent_attempt_limit: int = 5,
        prompt_limit: int = 8,
    ) -> tuple[str, ...]:
        with self.storage.connection() as conn:
            rows = conn.execute(
                """
                SELECT qqr.prompt
                FROM quiz_question_results AS qqr
                WHERE qqr.user_id = ?
                  AND qqr.is_correct = 1
                  AND qqr.attempt_id IN (
                      SELECT attempt_id
                      FROM quiz_attempts
                      WHERE user_id = ?
                      ORDER BY created_at DESC
                      LIMIT ?
                  )
                ORDER BY qqr.created_at DESC
                LIMIT ?
                """,
                (user_id, user_id, recent_attempt_limit, prompt_limit * 3),
            ).fetchall()

        prompts: list[str] = []
        seen: set[str] = set()
        for row in rows:
            prompt = row["prompt"].strip()
            normalized = prompt.casefold()
            if normalized in seen:
                continue
            seen.add(normalized)
            prompts.append(prompt)
            if len(prompts) >= prompt_limit:
                break
        return tuple(prompts)

    def list_pending_incorrect_questions(
        self,
        user_id: str,
        *,
        topic_id: str | None = None,
    ) -> list[Question]:
        query = """
            SELECT payload
            FROM pending_incorrect_questions
            WHERE user_id = ?
        """
        params: tuple[object, ...]
        if topic_id is None:
            params = (user_id,)
        else:
            query += " AND topic = ?"
            params = (user_id, topic_id)
        query += " ORDER BY first_incorrect_at ASC, prompt ASC"

        with self.storage.connection() as conn:
            rows = conn.execute(query, params).fetchall()

        return [_question_from_record(row["payload"]) for row in rows]

    def delete_for_user(self, user_id: str) -> None:
        with self.storage.connection() as conn:
            conn.execute("DELETE FROM quiz_attempts WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM pending_incorrect_questions WHERE user_id = ?", (user_id,))


@dataclass(slots=True)
class SQLiteWordbankRepository:
    storage: SQLiteStorage

    def upsert(self, entry: WordbankEntry) -> None:
        with self.storage.connection() as conn:
            conn.execute(
                """
                INSERT INTO wordbank (user_id, word, definition, topic, first_seen_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, word) DO UPDATE SET
                    definition = excluded.definition,
                    topic = excluded.topic,
                    first_seen_at = excluded.first_seen_at
                """,
                (
                    entry.user_id,
                    entry.word,
                    entry.definition,
                    entry.topic,
                    _serialize_datetime(entry.first_seen_at),
                ),
            )

    def update_definition(self, user_id: str, word: str, definition: str) -> None:
        """Update the definition for an existing wordbank entry for the user."""
        with self.storage.connection() as conn:
            conn.execute(
                """
                UPDATE wordbank
                SET definition = ?, first_seen_at = ?
                WHERE user_id = ? AND word = ?
                """,
                (definition, _serialize_datetime(datetime.now()), user_id, word),
            )

    def search_for_user(self, user_id: str, query: str = "", limit: int = 100) -> list[WordbankEntry]:
        with self.storage.connection() as conn:
            if query.strip():
                raw = query.strip().lower()
                pattern = f"%{raw}%"

                # Build a folded (ASCII) form of lower(word)/definition for diacritic-insensitive matching
                # Using nested REPLACE calls so SQLite can compare folded forms without changing schema.
                def folded_expr(col_name: str) -> str:
                    expr = f"lower({col_name})"
                    replacements = [
                        ("ă", "a"), ("â", "a"), ("î", "i"), ("ș", "s"), ("ş", "s"), ("ț", "t"), ("ţ", "t"),
                        ("Ă", "a"), ("Â", "a"), ("Î", "i"), ("Ș", "s"), ("Ş", "s"), ("Ț", "t"), ("Ţ", "t"),
                    ]
                    for a, b in replacements:
                        expr = f"REPLACE({expr}, '{a}', '{b}')"
                    return expr

                folded_pattern = raw
                # Fold the query on the Python side too so ASCII-only searches match folded data
                for a, b in [("ă", "a"), ("â", "a"), ("î", "i"), ("ș", "s"), ("ş", "s"), ("ț", "t"), ("ţ", "t")]:
                    folded_pattern = folded_pattern.replace(a, b)
                folded_pattern = f"%{folded_pattern}%"

                sql = f"""
                    SELECT *
                    FROM wordbank
                    WHERE user_id = ?
                      AND (
                        lower(word) LIKE ? OR lower(definition) LIKE ? OR lower(topic) LIKE ?
                        OR {folded_expr('word')} LIKE ? OR {folded_expr('definition')} LIKE ?
                      )
                    ORDER BY word ASC
                    LIMIT ?
                    """

                rows = conn.execute(sql, (user_id, pattern, pattern, pattern, folded_pattern, folded_pattern, limit)).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM wordbank
                    WHERE user_id = ?
                    ORDER BY word ASC
                    LIMIT ?
                    """,
                    (user_id, limit),
                ).fetchall()
        return [
            WordbankEntry(
                user_id=row["user_id"],
                word=row["word"],
                definition=row["definition"],
                topic=row["topic"],
                first_seen_at=_deserialize_datetime(row["first_seen_at"]) or datetime.now(),
            )
            for row in rows
        ]

    def delete_for_user(self, user_id: str) -> None:
        with self.storage.connection() as conn:
            conn.execute("DELETE FROM wordbank WHERE user_id = ?", (user_id,))


@dataclass(slots=True)
class SQLiteVerbbankRepository:
    storage: SQLiteStorage

    def upsert(self, entry: VerbbankEntry) -> None:
        with self.storage.connection() as conn:
            conn.execute(
                """
                INSERT INTO verbbank (user_id, verb, conjugations, translation, topic, first_seen_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, verb) DO UPDATE SET
                    conjugations = excluded.conjugations,
                    translation = excluded.translation,
                    topic = excluded.topic,
                    first_seen_at = excluded.first_seen_at
                """,
                (
                    entry.user_id,
                    entry.verb,
                    entry.conjugations,
                    entry.translation,
                    entry.topic,
                    _serialize_datetime(entry.first_seen_at),
                ),
            )

    def update_conjugations(self, user_id: str, verb: str, conjugations: str) -> None:
        with self.storage.connection() as conn:
            conn.execute(
                """
                UPDATE verbbank
                SET conjugations = ?, first_seen_at = ?
                WHERE user_id = ? AND verb = ?
                """,
                (conjugations, _serialize_datetime(datetime.now()), user_id, verb),
            )

    def search_for_user(self, user_id: str, query: str = "", limit: int = 100) -> list[VerbbankEntry]:
        with self.storage.connection() as conn:
            if query.strip():
                raw = query.strip().lower()
                pattern = f"%{raw}%"

                def folded_expr(col_name: str) -> str:
                    expr = f"lower({col_name})"
                    replacements = [
                        ("ă", "a"), ("â", "a"), ("î", "i"), ("ș", "s"), ("ş", "s"), ("ț", "t"), ("ţ", "t"),
                        ("Ă", "a"), ("Â", "a"), ("Î", "i"), ("Ș", "s"), ("Ş", "s"), ("Ț", "t"), ("Ţ", "t"),
                    ]
                    for a, b in replacements:
                        expr = f"REPLACE({expr}, '{a}', '{b}')"
                    return expr

                folded_pattern = raw
                for a, b in [("ă", "a"), ("â", "a"), ("î", "i"), ("ș", "s"), ("ş", "s"), ("ț", "t"), ("ţ", "t")]:
                    folded_pattern = folded_pattern.replace(a, b)
                folded_pattern = f"%{folded_pattern}%"

                sql = f"""
                    SELECT *
                    FROM verbbank
                    WHERE user_id = ?
                      AND (
                        lower(verb) LIKE ? OR lower(conjugations) LIKE ? OR lower(translation) LIKE ? OR lower(topic) LIKE ?
                        OR {folded_expr('verb')} LIKE ? OR {folded_expr('conjugations')} LIKE ? OR {folded_expr('translation')} LIKE ?
                      )
                    ORDER BY verb ASC
                    LIMIT ?
                    """

                rows = conn.execute(sql, (user_id, pattern, pattern, pattern, pattern, folded_pattern, folded_pattern, folded_pattern, limit)).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM verbbank
                    WHERE user_id = ?
                    ORDER BY verb ASC
                    LIMIT ?
                    """,
                    (user_id, limit),
                ).fetchall()
        return [
            VerbbankEntry(
                user_id=row["user_id"],
                verb=row["verb"],
                conjugations=row["conjugations"],
                translation=(row["translation"] if "translation" in row.keys() else ""),
                topic=row["topic"],
                first_seen_at=_deserialize_datetime(row["first_seen_at"]) or datetime.now(),
            )
            for row in rows
        ]

    def delete_for_user(self, user_id: str) -> None:
        with self.storage.connection() as conn:
            conn.execute("DELETE FROM verbbank WHERE user_id = ?", (user_id,))


@dataclass(slots=True)
class SQLiteOfflineQuestionRepository:
    storage: SQLiteStorage

    def upsert_questions(
        self,
        topic_id: str,
        questions: Sequence[Question],
        *,
        provider_name: str | None = None,
        model: str | None = None,
    ) -> int:
        now = _serialize_datetime(datetime.now()) or datetime.now().isoformat()
        rows = [
            (
                _question_fingerprint(topic_id, question),
                topic_id,
                question.prompt,
                question.question_type.value,
                question.difficulty_rating,
                question.cefr_band.value,
                question.correct_answer,
                question.explanation,
                json.dumps(question.tags, ensure_ascii=False),
                json.dumps(question.options, ensure_ascii=False),
                question.hint,
                json.dumps(question.rubric, ensure_ascii=False),
                provider_name,
                model,
                now,
                now,
            )
            for question in questions
        ]
        if not rows:
            return 0

        with self.storage.connection() as conn:
            conn.executemany(
                """
                INSERT INTO offline_question_bank (
                    fingerprint, topic, prompt, question_type, difficulty_rating, cefr_band,
                    correct_answer, explanation, tags, options, hint, rubric,
                    provider_name, model, created_at, last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    difficulty_rating = excluded.difficulty_rating,
                    cefr_band = excluded.cefr_band,
                    explanation = excluded.explanation,
                    tags = excluded.tags,
                    options = excluded.options,
                    hint = excluded.hint,
                    rubric = excluded.rubric,
                    provider_name = excluded.provider_name,
                    model = excluded.model,
                    last_seen_at = excluded.last_seen_at
                """,
                rows,
            )
        return len(rows)

    def list_for_topic(self, topic_id: str, limit: int | None = None) -> list[Question]:
        query = """
            SELECT *
            FROM offline_question_bank
            WHERE topic = ?
            ORDER BY last_seen_at DESC, created_at DESC
        """
        params: tuple[object, ...]
        if limit is None:
            params = (topic_id,)
        else:
            query += " LIMIT ?"
            params = (topic_id, limit)

        with self.storage.connection() as conn:
            rows = conn.execute(query, params).fetchall()

        questions: list[Question] = []
        for index, row in enumerate(rows, start=1):
            questions.append(
                Question(
                    question_id=f"offline-{topic_id}-{index}",
                    prompt=row["prompt"],
                    question_type=QuestionType(row["question_type"]),
                    difficulty_rating=row["difficulty_rating"],
                    cefr_band=CEFRBand(row["cefr_band"]),
                    correct_answer=row["correct_answer"],
                    explanation=row["explanation"],
                    tags=list(json.loads(row["tags"])),
                    options=list(json.loads(row["options"])),
                    hint=row["hint"],
                    rubric=dict(json.loads(row["rubric"])),
                )
            )
        return questions

    def count_for_topic(self, topic_id: str) -> int:
        with self.storage.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS question_count FROM offline_question_bank WHERE topic = ?",
                (topic_id,),
            ).fetchone()
        return int(row["question_count"]) if row is not None else 0

    def count_all(self) -> int:
        with self.storage.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS question_count FROM offline_question_bank",
            ).fetchone()
        return int(row["question_count"]) if row is not None else 0

    def delete_all(self) -> int:
        with self.storage.connection() as conn:
            cursor = conn.execute("DELETE FROM offline_question_bank")
        return int(cursor.rowcount if cursor.rowcount is not None else 0)
