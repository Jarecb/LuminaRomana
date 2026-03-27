from app.models import CEFRBand, QuizAttempt, UserProgress
from app.services import ContentLibrary, DifficultyManager, SessionAction


def test_difficulty_manager_uses_last_three_scores_for_average():
    manager = DifficultyManager(ContentLibrary())

    average = manager.rolling_average([40.0, 75.0, 90.0, 96.0])

    assert average == (75.0 + 90.0 + 96.0) / 3


def test_difficulty_manager_triggers_review_and_decreases_difficulty():
    manager = DifficultyManager(ContentLibrary())
    progress = UserProgress(
        user_id="learner-1",
        current_difficulty=4,
        recent_scores=[88.0, 82.0, 55.0],
    )

    assessment = manager.assess_user(progress)

    assert assessment.action == SessionAction.REVIEW
    assert assessment.review_required is True
    assert assessment.next_difficulty == 3
    assert assessment.recommended_cefr_band == CEFRBand.A1


def test_difficulty_manager_increases_difficulty_for_strong_recent_performance():
    manager = DifficultyManager(ContentLibrary())
    progress = UserProgress(
        user_id="learner-1",
        current_difficulty=5,
        recent_scores=[84.0, 88.0, 94.0],
    )

    assessment = manager.assess_user(progress)

    assert assessment.action == SessionAction.ADVANCE
    assert assessment.review_required is False
    assert assessment.next_difficulty == 6
    assert assessment.recommended_cefr_band == CEFRBand.A2


def test_prompt_constraints_reduce_context_during_review():
    manager = DifficultyManager(ContentLibrary())
    progress = UserProgress(
        user_id="learner-1",
        current_level=8,
        current_cefr_band=CEFRBand.B1,
        current_difficulty=7,
        recent_scores=[78.0, 74.0, 58.0],
        skill_scores={"reading": 82.0, "writing": 79.0},
    )

    constraints = manager.build_prompt_constraints(progress, focus_tags=("cases", "agreement"))

    assert constraints.session_goal == "review"
    assert constraints.vocabulary_profile == "simpler_vocabulary"
    assert constraints.include_hints is True
    assert constraints.max_context_sentences == 2
    assert constraints.focus_tags == ("cases", "agreement")


def test_review_session_prioritizes_blocking_topics_and_common_mistakes():
    manager = DifficultyManager(ContentLibrary())
    progress = UserProgress(
        user_id="learner-1",
        current_level=9,
        current_cefr_band=CEFRBand.B1,
        current_difficulty=8,
        recent_scores=[81.0, 59.0],
        mastery_matrix={
            "romanian_basics": 0.95,
            "nouns_and_articles": 0.87,
            "core_cases": 0.83,
            "present_tense_verbs": 0.80,
            "pronouns_and_tenses": 0.79,
            "connected_communication": 0.76,
            "narrative_b1_grammar": 0.62,
            "b1_b2_transition": 0.58,
        },
    )
    attempts = [
        QuizAttempt(
            attempt_id="attempt-1",
            user_id="learner-1",
            lesson_id="lesson-1",
            score_percent=59.0,
            mistake_tags=["relative_clauses", "relative_clauses", "conditional"],
        )
    ]

    review = manager.build_review_session(progress, attempts, topic_id="b2_core_structures")

    assert review.recommended_topics == ("narrative_b1_grammar", "b1_b2_transition")
    assert review.focus_tags == ("relative_clauses", "conditional")
    assert review.recheck_mastery_topics == review.recommended_topics
