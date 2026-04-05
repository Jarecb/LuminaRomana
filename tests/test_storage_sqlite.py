from pathlib import Path

from app.models import CEFRBand, ExampleSentence, Lesson, Question, QuestionType, QuizAttempt, UserProgress, WordbankEntry
from app.storage import (
    SQLiteLessonRepository,
    SQLiteQuizAttemptRepository,
    SQLiteStorage,
    SQLiteUserProgressRepository,
    SQLiteWordbankRepository,
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


def test_wordbank_entries_are_stored_and_searchable(tmp_path):
    storage = build_storage(tmp_path)
    user_repository = SQLiteUserProgressRepository(storage)
    wordbank_repository = SQLiteWordbankRepository(storage)

    user_repository.save(UserProgress(user_id="learner-1"))
    wordbank_repository.upsert(
        WordbankEntry(
            user_id="learner-1",
            word="baiatul",
            definition="the boy",
            topic="nouns_and_articles",
        )
    )
    wordbank_repository.upsert(
        WordbankEntry(
            user_id="learner-1",
            word="cadoul",
            definition="the gift",
            topic="nouns_and_articles",
        )
    )

    all_entries = wordbank_repository.search_for_user("learner-1")
    filtered_entries = wordbank_repository.search_for_user("learner-1", query="gift")

    assert [entry.word for entry in all_entries] == ["baiatul", "cadoul"]
    assert [entry.word for entry in filtered_entries] == ["cadoul"]


def test_pending_incorrect_questions_persist_until_answered_correctly(tmp_path):
    storage = build_storage(tmp_path)
    user_repository = SQLiteUserProgressRepository(storage)
    lesson_repository = SQLiteLessonRepository(storage)
    attempt_repository = SQLiteQuizAttemptRepository(storage)

    user_repository.save(UserProgress(user_id="learner-1"))
    lesson = build_sample_lesson()
    lesson_repository.save("learner-1", lesson)

    first_attempt = QuizAttempt(
        attempt_id="attempt-incorrect",
        user_id="learner-1",
        lesson_id=lesson.lesson_id,
        score_percent=0.0,
        mistake_tags=["definite_articles"],
    )
    attempt_repository.save(first_attempt)
    attempt_repository.save_question_results(
        attempt=first_attempt,
        topic_id=lesson.topic,
        results=((lesson.quiz_questions[0], False),),
    )

    pending_after_incorrect = attempt_repository.list_pending_incorrect_questions(
        "learner-1",
        topic_id=lesson.topic,
    )

    assert len(pending_after_incorrect) == 1
    assert pending_after_incorrect[0].prompt == lesson.quiz_questions[0].prompt

    second_attempt = QuizAttempt(
        attempt_id="attempt-correct",
        user_id="learner-1",
        lesson_id=lesson.lesson_id,
        score_percent=100.0,
        mistake_tags=[],
    )
    attempt_repository.save(second_attempt)
    attempt_repository.save_question_results(
        attempt=second_attempt,
        topic_id=lesson.topic,
        results=((lesson.quiz_questions[0], True),),
    )

    assert attempt_repository.list_pending_incorrect_questions("learner-1", topic_id=lesson.topic) == []
