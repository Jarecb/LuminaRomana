from datetime import datetime, timezone

import pytest

from app.models import CEFRBand, Lesson, Question, QuestionType, QuizAttempt, UserProgress


def test_user_progress_records_recent_scores_and_mastery():
    progress = UserProgress(user_id="learner-1")

    progress.update_mastery("romanian_basics", 0.75)
    progress.update_skill_score("grammar", 82.0)
    progress.record_quiz_attempt(55.0, completed_at=datetime(2026, 3, 27, tzinfo=timezone.utc))
    progress.record_quiz_attempt(71.0)
    progress.record_quiz_attempt(92.0)
    progress.record_quiz_attempt(88.0)

    assert progress.mastery_matrix["romanian_basics"] == 0.75
    assert progress.skill_scores["grammar"] == 82.0
    assert progress.recent_scores == [71.0, 92.0, 88.0]
    assert progress.total_xp == 306
    assert progress.last_lesson_at is not None


def test_question_rejects_missing_correct_answer_in_options():
    with pytest.raises(ValueError, match="correct answer"):
        Question(
            question_id="q-1",
            prompt="Choose the correct form.",
            question_type=QuestionType.MULTIPLE_CHOICE,
            difficulty_rating=3,
            cefr_band=CEFRBand.A1,
            correct_answer="pomul",
            explanation="The definite form is required here.",
            tags=["definite_articles"],
            options=["pom", "pomi"],
        )


def test_quiz_attempt_validates_score_bounds():
    with pytest.raises(ValueError, match="between 0 and 100"):
        QuizAttempt(
            attempt_id="attempt-1",
            user_id="learner-1",
            lesson_id="lesson-1",
            score_percent=120.0,
        )


def test_lesson_validates_explanation_text():
    question = Question(
        question_id="q-1",
        prompt="Choose the correct form.",
        question_type=QuestionType.MULTIPLE_CHOICE,
        difficulty_rating=2,
        cefr_band=CEFRBand.A1,
        correct_answer="eu sunt",
        explanation="This is the present tense of 'a fi' for 'I'.",
        tags=["a_fi_present"],
        options=["eu sunt", "eu este"],
    )

    with pytest.raises(ValueError, match="explanation text"):
        Lesson(
            lesson_id="lesson-1",
            topic="romanian_basics",
            level=1,
            cefr_band=CEFRBand.A1,
            difficulty=2,
            explanation_text=" ",
            example_sentences=[],
            key_rules=[],
            quiz_questions=[question],
        )
