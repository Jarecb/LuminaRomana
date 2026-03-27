from pathlib import Path

from app.models import CEFRBand, ExampleSentence, Lesson, Question, QuestionType, QuizAttempt, UserProgress
from app.storage import (
    SQLiteLessonRepository,
    SQLiteQuizAttemptRepository,
    SQLiteStorage,
    SQLiteUserProgressRepository,
)


def build_storage(tmp_path: Path) -> SQLiteStorage:
    storage = SQLiteStorage(tmp_path / "lumina_romana.db")
    storage.initialize()
    return storage


def build_sample_lesson() -> Lesson:
    return Lesson(
        lesson_id="lesson-1",
        topic="nouns_and_articles",
        level=2,
        cefr_band=CEFRBand.A1,
        difficulty=3,
        explanation_text="Romanian attaches the definite article to the noun.",
        example_sentences=[
            ExampleSentence(romanian="Baiatul este aici.", english="The boy is here."),
        ],
        key_rules=["Masculine singular nouns often take '-ul' in the definite form."],
        quiz_questions=[
            Question(
                question_id="question-1",
                prompt="Choose the correct form for 'the boy'.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                difficulty_rating=3,
                cefr_band=CEFRBand.A1,
                correct_answer="baiatul",
                explanation="The masculine singular definite ending is '-ul'.",
                tags=["definite_articles", "masculine_nouns"],
                options=["baiat", "baiatul", "baieti"],
                hint="Look for the singular definite form.",
            )
        ],
    )


def test_user_progress_round_trips_through_sqlite(tmp_path):
    storage = build_storage(tmp_path)
    repository = SQLiteUserProgressRepository(storage)
    progress = UserProgress(
        user_id="learner-1",
        current_level=2,
        current_cefr_band=CEFRBand.A1,
        current_difficulty=3,
        total_xp=125,
    )
    progress.update_mastery("nouns_and_articles", 0.8)
    progress.update_skill_score("grammar", 78.0)
    progress.record_quiz_attempt(65.0)
    progress.record_quiz_attempt(88.0)

    repository.save(progress)
    restored = repository.get("learner-1")

    assert restored is not None
    assert restored.current_level == 2
    assert restored.current_difficulty == 3
    assert restored.mastery_matrix == {"nouns_and_articles": 0.8}
    assert restored.skill_scores == {"grammar": 78.0}
    assert restored.recent_scores == [65.0, 88.0]


def test_lessons_and_attempts_are_stored_and_retrieved(tmp_path):
    storage = build_storage(tmp_path)
    user_repository = SQLiteUserProgressRepository(storage)
    lesson_repository = SQLiteLessonRepository(storage)
    attempt_repository = SQLiteQuizAttemptRepository(storage)

    user_repository.save(UserProgress(user_id="learner-1"))
    lesson = build_sample_lesson()
    lesson_repository.save("learner-1", lesson)
    attempt_repository.save(
        QuizAttempt(
            attempt_id="attempt-1",
            user_id="learner-1",
            lesson_id=lesson.lesson_id,
            score_percent=72.5,
            mistake_tags=["definite_articles"],
        )
    )

    restored_lesson = lesson_repository.get("lesson-1")
    lesson_history = lesson_repository.list_for_user("learner-1")
    attempts = attempt_repository.list_for_user("learner-1")

    assert restored_lesson is not None
    assert restored_lesson.topic == "nouns_and_articles"
    assert restored_lesson.quiz_questions[0].correct_answer == "baiatul"
    assert len(lesson_history) == 1
    assert lesson_history[0].lesson_id == "lesson-1"
    assert len(attempts) == 1
    assert attempts[0].score_percent == 72.5
    assert attempts[0].mistake_tags == ["definite_articles"]
