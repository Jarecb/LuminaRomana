from __future__ import annotations

import logging

from app.ai import AIService, PromptBuilder
from app.ai.types import LessonGenerationResult
from app.ai.providers import DisabledAIProvider
from app.models import CEFRBand, Lesson, Question, QuestionType, UserProgress
from app.services import ContentLibrary, DifficultyManager
from app.services.learning import LearningService
from app.storage import (
    SQLiteLessonRepository,
    SQLiteOfflineQuestionRepository,
    SQLiteQuizAttemptRepository,
    SQLiteStorage,
    SQLiteUserProgressRepository,
    SQLiteWordbankRepository,
)
from app.validation import ContentValidator


def build_learning_service(tmp_path):
    storage = SQLiteStorage(tmp_path / "lumina_romana.db")
    storage.initialize()
    offline_repository = SQLiteOfflineQuestionRepository(storage)
    content_library = ContentLibrary(offline_question_repository=offline_repository)
    difficulty_manager = DifficultyManager(content_library)
    return LearningService(
        user_progress_repository=SQLiteUserProgressRepository(storage),
        lesson_repository=SQLiteLessonRepository(storage),
        quiz_attempt_repository=SQLiteQuizAttemptRepository(storage),
        wordbank_repository=SQLiteWordbankRepository(storage),
        content_library=content_library,
        difficulty_manager=difficulty_manager,
        ai_service=AIService(
            provider=DisabledAIProvider(),
            prompt_builder=PromptBuilder(),
            content_library=content_library,
            difficulty_manager=difficulty_manager,
            content_validator=ContentValidator(),
            logger=logging.getLogger("test.learning"),
            max_retries=1,
            offline_question_repository=offline_repository,
        ),
    )


def build_offline_question(topic_id: str, index: int) -> Question:
    return Question(
        question_id=f"offline-{topic_id}-{index}",
        prompt=f"Unique prompt {index}: choose the correct form for {topic_id}.",
        question_type=QuestionType.MULTIPLE_CHOICE,
        difficulty_rating=2,
        cefr_band=CEFRBand.A1,
        correct_answer=f"answer-{index}",
        explanation=f"Explanation for question {index}.",
        tags=[topic_id],
        options=[f"answer-{index}", f"distractor-{index}-a", f"distractor-{index}-b"],
        hint="Pick the exact matching answer.",
    )


def test_start_session_generates_fallback_lesson_and_can_resume(tmp_path):
    service = build_learning_service(tmp_path)

    first_session = service.start_or_resume_session()
    revision = service.build_level_revision("default-learner", first_session.topic.topic_id)
    lesson_session = service.start_topic_lesson(first_session.topic.topic_id)
    resumed_session = service.start_or_resume_session()

    assert first_session.page_kind == "intro"
    assert first_session.topic.topic_id == "romanian_basics"
    assert first_session.session_goal == "lesson"
    assert revision.vocabulary
    assert lesson_session.lesson is not None
    assert lesson_session.lesson.topic == "romanian_basics"
    assert lesson_session.source == "fallback"
    assert resumed_session.resumed is True
    assert resumed_session.lesson is not None
    assert resumed_session.lesson.lesson_id == lesson_session.lesson.lesson_id


def test_start_or_resume_lesson_session_generates_lesson_immediately(tmp_path):
    service = build_learning_service(tmp_path)

    session = service.start_or_resume_lesson_session()
    resumed = service.start_or_resume_lesson_session()
    wordbank = service.build_wordbank()

    assert session.page_kind == "lesson"
    assert session.lesson is not None
    assert session.lesson.topic == "romanian_basics"
    assert session.source == "fallback"
    assert resumed.resumed is True
    assert resumed.lesson is not None
    assert resumed.lesson.lesson_id == session.lesson.lesson_id
    assert any(entry.topic == "romanian_basics" for entry in wordbank.entries)


def test_start_or_resume_lesson_session_adds_example_sentence_words_to_wordbank(tmp_path):
    service = build_learning_service(tmp_path)

    session = service.start_or_resume_lesson_session()
    wordbank = service.build_wordbank()

    assert session.lesson is not None
    assert any(
        entry.word == "ana" and entry.definition == "Seen in example: Hello, I am Ana."
        for entry in wordbank.entries
    )


def test_submit_quiz_requires_five_sets_plus_page_and_average_to_advance_topic(tmp_path):
    service = build_learning_service(tmp_path)
    intro = service.start_or_resume_session()
    revision = service.build_level_revision("default-learner", intro.topic.topic_id)
    session = service.start_topic_lesson(intro.topic.topic_id)
    assert revision.vocabulary
    assert session.lesson is not None

    results = []
    score_plan = [60, 100, 80, 80, 80]
    current_session = session
    for planned_score in score_plan:
        assert current_session.lesson is not None
        answers = {}
        correct_needed = int((planned_score / 100) * len(current_session.lesson.quiz_questions))
        for index, question in enumerate(current_session.lesson.quiz_questions):
            answers[question.question_id] = question.correct_answer if index < correct_needed else ""
        results.append(service.submit_quiz(current_session.lesson.lesson_id, answers))
        if planned_score != score_plan[-1]:
            current_session = service.start_or_resume_session()
            assert current_session.page_kind == "revision"
            assert current_session.level_revision is not None
            current_session = service.start_topic_lesson(current_session.topic.topic_id)
            assert current_session.lesson is not None

    first_result = results[0]
    final_result = results[-1]
    remediation_session = service.start_or_resume_lesson_session()
    assert remediation_session.lesson is not None
    remediation_result = service.submit_quiz(
        remediation_session.lesson.lesson_id,
        {
            question.question_id: question.correct_answer
            for question in remediation_session.lesson.quiz_questions
        },
    )
    dashboard = service.build_dashboard()

    assert first_result.score_percent == 60.0
    assert first_result.average_score_percent == 60.0
    assert first_result.action == "review"
    assert final_result.score_percent == 80.0
    assert final_result.average_score_percent == 80.0
    assert final_result.topic_attempts == 5
    assert final_result.action == "remediation"
    assert final_result.updated_progress.current_level == 1
    assert remediation_result.action == "advance"
    assert remediation_result.updated_progress.current_level == 2
    assert remediation_result.updated_progress.current_difficulty == 4
    assert remediation_result.updated_progress.current_cefr_band == CEFRBand.A1
    assert dashboard.next_topic is not None
    assert dashboard.next_topic.topic_id == "nouns_and_articles"


def test_low_score_triggers_review_session(tmp_path):
    service = build_learning_service(tmp_path)
    intro = service.start_or_resume_session()
    session = service.start_topic_lesson(intro.topic.topic_id)
    assert session.lesson is not None

    result = service.submit_quiz(
        session.lesson.lesson_id,
        {question.question_id: "" for question in session.lesson.quiz_questions},
    )
    review_session = service.start_or_resume_session()

    assert result.score_percent == 0.0
    assert result.action == "review"
    assert review_session.page_kind == "revision"
    assert review_session.session_goal == "review"
    assert review_session.level_revision is not None
    assert review_session.topic.topic_id == "romanian_basics"


def test_advancement_is_blocked_until_pending_incorrect_answers_are_cleared(tmp_path):
    service = build_learning_service(tmp_path)
    intro = service.start_or_resume_session()
    session = service.start_topic_lesson(intro.topic.topic_id)
    assert session.lesson is not None

    current_session = session
    results = []
    first_question = None
    for attempt_index in range(5):
        assert current_session.lesson is not None
        answers = {
            question.question_id: question.correct_answer
            for question in current_session.lesson.quiz_questions
        }
        if attempt_index == 4:
            first_question = current_session.lesson.quiz_questions[0]
            answers[first_question.question_id] = ""
        results.append(service.submit_quiz(current_session.lesson.lesson_id, answers))
        if attempt_index < 4:
            current_session = service.start_or_resume_session()
            assert current_session.page_kind == "revision"
            current_session = service.start_topic_lesson(current_session.topic.topic_id)
            assert current_session.lesson is not None

    blocked_result = results[-1]
    remediation_session = service.start_or_resume_lesson_session()

    assert first_question is not None
    assert blocked_result.action == "remediation"
    assert blocked_result.topic_passed is False
    assert blocked_result.pending_incorrect_count == 1
    assert blocked_result.updated_progress.current_level == 1
    assert blocked_result.next_topic is not None
    assert blocked_result.next_topic.topic_id == "romanian_basics"
    assert remediation_session.lesson is not None
    assert remediation_session.session_goal == "remediation"
    assert remediation_session.lesson.lesson_id.startswith("remediation-romanian_basics-")
    assert len(remediation_session.lesson.quiz_questions) == 1
    assert remediation_session.lesson.quiz_questions[0].prompt == first_question.prompt

    remediation_result = service.submit_quiz(
        remediation_session.lesson.lesson_id,
        {
            remediation_session.lesson.quiz_questions[0].question_id:
                remediation_session.lesson.quiz_questions[0].correct_answer
        },
    )
    dashboard = service.build_dashboard()

    assert remediation_result.action == "advance"
    assert remediation_result.pending_incorrect_count == 0
    assert remediation_result.topic_passed is True
    assert remediation_result.updated_progress.current_level == 2
    assert dashboard.next_topic is not None
    assert dashboard.next_topic.topic_id == "nouns_and_articles"


def test_start_topic_lesson_replaces_duplicate_questions_with_unique_alternatives(tmp_path):
    service = build_learning_service(tmp_path)
    topic = service.content_library.get_topic("romanian_basics")
    assert topic is not None

    duplicate_question = Question(
        question_id="duplicate-q1",
        prompt="Choose the correct Romanian form of 'I am'.",
        question_type=QuestionType.MULTIPLE_CHOICE,
        difficulty_rating=2,
        cefr_band=CEFRBand.A1,
        correct_answer="sunt",
        explanation="'Eu sunt' means 'I am'.",
        tags=["romanian_basics", "a_fi_present"],
        options=["este", "sunt", "suntem", "esti"],
        hint="Match the form used with 'eu'.",
    )
    duplicate_lesson = Lesson(
        lesson_id="duplicate-lesson",
        topic=topic.topic_id,
        level=topic.level,
        cefr_band=topic.cefr_band,
        difficulty=2,
        explanation_text="Duplicate test lesson.",
        example_sentences=[],
        key_rules=["Use the correct form of a fi."],
        quiz_questions=[
            duplicate_question,
            Question(
                question_id="duplicate-q2",
                prompt=duplicate_question.prompt,
                question_type=duplicate_question.question_type,
                difficulty_rating=duplicate_question.difficulty_rating,
                cefr_band=duplicate_question.cefr_band,
                correct_answer=duplicate_question.correct_answer,
                explanation=duplicate_question.explanation,
                tags=list(duplicate_question.tags),
                options=list(duplicate_question.options),
                hint=duplicate_question.hint,
            ),
            build_offline_question(topic.topic_id, 1),
            build_offline_question(topic.topic_id, 2),
            build_offline_question(topic.topic_id, 3),
        ],
    )

    service.ai_service.generate_lesson = lambda request: LessonGenerationResult(
        lesson=duplicate_lesson,
        lesson_payload={},
        provider_name="test",
        model="duplicate-fixture",
        prompt=None,
        attempts=1,
        source="ai",
    )

    session = service.start_topic_lesson(topic.topic_id)

    assert session.lesson is not None
    prompts = [question.prompt for question in session.lesson.quiz_questions]
    assert len(prompts) == len(set(prompts))
    assert len(session.lesson.quiz_questions) == 5
    assert any("duplicate questions" in warning.lower() for warning in session.warnings)


def test_dashboard_creates_default_user_progress(tmp_path):
    service = build_learning_service(tmp_path)

    dashboard = service.build_dashboard()

    assert dashboard.user_progress == UserProgress(user_id="default-learner")
    assert dashboard.next_topic is not None
    assert dashboard.next_topic.topic_id == "romanian_basics"


def test_level_intro_contains_descriptive_grammar_explanations(tmp_path):
    service = build_learning_service(tmp_path)

    intro = service.build_level_intro("default-learner", "nouns_and_articles")
    cases_intro = service.build_level_intro("default-learner", "core_cases")

    assert any("-ul" in principle for principle in intro.principles)
    assert any("lui" in principle for principle in cases_intro.principles)


def test_level_revision_contains_curated_vocabulary(tmp_path):
    service = build_learning_service(tmp_path)

    revision = service.build_level_revision("default-learner", "nouns_and_articles")
    wordbank = service.build_wordbank()

    assert ("baiatul", "the boy") in revision.vocabulary
    assert ("cadoul", "the gift") in revision.vocabulary
    assert any(entry.word == "baiatul" for entry in wordbank.entries)
    assert any(entry.definition == "the gift" for entry in wordbank.entries)


def test_submit_quiz_ignores_capitalization_and_trailing_full_stop(tmp_path):
    service = build_learning_service(tmp_path)

    assert service._answers_match("I am a student.", "i am a student") is True


def test_wrong_answer_feedback_explains_why_it_is_wrong(tmp_path):
    service = build_learning_service(tmp_path)
    intro = service.start_or_resume_session()
    session = service.start_topic_lesson(intro.topic.topic_id)
    assert session.lesson is not None

    result = service.submit_quiz(
        session.lesson.lesson_id,
        {question.question_id: "" for question in session.lesson.quiz_questions},
    )

    incorrect = next(item for item in result.feedback if not item.is_correct)
    assert incorrect.why_wrong is not None
    assert "expected answer" in incorrect.why_wrong


def test_submit_quiz_updates_integrated_grammar_skill_for_b1_lesson(tmp_path):
    service = build_learning_service(tmp_path)
    progress = service.get_or_create_user_progress()
    progress.current_level = 7
    progress.current_cefr_band = CEFRBand.B1
    progress.current_difficulty = 7
    progress.mastery_matrix.update(
        {
            "romanian_basics": 0.9,
            "nouns_and_articles": 0.88,
            "core_cases": 0.86,
            "present_tense_verbs": 0.84,
            "pronouns_and_tenses": 0.82,
            "connected_communication": 0.8,
        }
    )
    service.user_progress_repository.save(progress)

    session = service.start_topic_lesson("narrative_b1_grammar")
    assert session.lesson is not None

    result = service.submit_quiz(
        session.lesson.lesson_id,
        {question.question_id: question.correct_answer for question in session.lesson.quiz_questions},
    )

    assert result.updated_progress.skill_scores["grammar"] == 100.0
    assert result.updated_progress.skill_scores["integrated_grammar"] == 100.0
    assert result.updated_progress.current_cefr_band == CEFRBand.B1


def test_evaluate_placement_can_classify_through_b1(tmp_path):
    service = build_learning_service(tmp_path)

    outcome = service.evaluate_placement(
        {
            "placement_a1_foundations": 92.0,
            "placement_a2_everyday_use": 81.0,
            "placement_b1_functional_range": 74.0,
            "placement_b2_integrated_control": 41.0,
        }
    )

    assert outcome.cefr_band == "B1"
    assert outcome.suggested_level == 7
    assert outcome.suggested_topic_id == "narrative_b1_grammar"


def test_submit_quiz_updates_reading_and_writing_skills_for_b2_lesson(tmp_path):
    service = build_learning_service(tmp_path)
    progress = service.get_or_create_user_progress()
    progress.current_level = 9
    progress.current_cefr_band = CEFRBand.B2
    progress.current_difficulty = 9
    progress.mastery_matrix.update(
        {
            "romanian_basics": 0.9,
            "nouns_and_articles": 0.88,
            "core_cases": 0.86,
            "present_tense_verbs": 0.84,
            "pronouns_and_tenses": 0.82,
            "connected_communication": 0.8,
            "narrative_b1_grammar": 0.8,
            "b1_b2_transition": 0.8,
        }
    )
    service.user_progress_repository.save(progress)

    session = service.start_topic_lesson("b2_core_structures")
    assert session.lesson is not None

    result = service.submit_quiz(
        session.lesson.lesson_id,
        {question.question_id: question.correct_answer for question in session.lesson.quiz_questions},
    )

    assert result.updated_progress.skill_scores["grammar"] == 100.0
    assert result.updated_progress.skill_scores["integrated_grammar"] == 100.0
    assert result.updated_progress.skill_scores["reading"] == 100.0
    assert result.updated_progress.skill_scores["writing"] == 100.0


def test_evaluate_placement_can_classify_through_b2(tmp_path):
    service = build_learning_service(tmp_path)

    outcome = service.evaluate_placement(
        {
            "placement_a1_foundations": 95.0,
            "placement_a2_everyday_use": 88.0,
            "placement_b1_functional_range": 80.0,
            "placement_b2_integrated_control": 76.0,
        }
    )

    assert outcome.cefr_band == "B2"
    assert outcome.suggested_level == 9
    assert outcome.suggested_topic_id == "b2_core_structures"


def test_set_testing_position_resets_state_and_jumps_to_requested_band(tmp_path):
    service = build_learning_service(tmp_path)
    intro = service.start_or_resume_session()
    session = service.start_topic_lesson(intro.topic.topic_id)
    assert session.lesson is not None

    progress = service.set_testing_position(level=7)
    dashboard = service.build_dashboard()

    assert progress.current_level == 7
    assert progress.current_cefr_band == CEFRBand.B1
    assert progress.current_difficulty == 7
    assert progress.mastery_matrix["connected_communication"] == service.difficulty_manager.b2_prerequisite_threshold
    assert service.get_active_lesson() is None
    assert dashboard.next_topic is not None
    assert dashboard.next_topic.topic_id == "narrative_b1_grammar"


def test_practice_replay_does_not_reduce_overall_progress(tmp_path):
    service = build_learning_service(tmp_path)
    progress = service.get_or_create_user_progress()
    progress.current_level = 5
    progress.current_cefr_band = CEFRBand.A2
    progress.current_difficulty = 5
    progress.update_mastery("romanian_basics", 0.9)
    progress.update_mastery("nouns_and_articles", 0.88)
    progress.update_mastery("core_cases", 0.86)
    progress.update_mastery("present_tense_verbs", 0.84)
    service.user_progress_repository.save(progress)

    session = service.start_topic_lesson("romanian_basics", session_goal_override="practice")
    assert session.lesson is not None
    assert session.session_goal == "practice"

    result = service.submit_quiz(
        session.lesson.lesson_id,
        {question.question_id: "" for question in session.lesson.quiz_questions},
    )
    updated = service.get_or_create_user_progress()

    assert result.action == "practice"
    assert updated.current_level == 5
    assert updated.current_cefr_band == CEFRBand.A2
    assert updated.mastery_matrix["present_tense_verbs"] == 0.84
    assert updated.mastery_matrix["romanian_basics"] == 0.9


def test_start_or_resume_lesson_session_skips_saved_lesson_with_missing_dialogue_context(tmp_path):
    service = build_learning_service(tmp_path)
    progress = service.get_or_create_user_progress()
    service.user_progress_repository.save(progress)
    broken_lesson = Lesson(
        lesson_id="broken-lesson",
        topic="romanian_basics",
        level=1,
        cefr_band=CEFRBand.A1,
        difficulty=2,
        explanation_text="Broken saved lesson.",
        example_sentences=[],
        key_rules=["Use a fi."],
        quiz_questions=[
            Question(
                question_id="q-broken",
                prompt="Complete the dialogue with the appropriate forms of a fi.",
                question_type=QuestionType.FILL_IN_THE_BLANK,
                difficulty_rating=2,
                cefr_band=CEFRBand.A1,
                correct_answer="sunt",
                explanation="Needs an actual dialogue to be answerable.",
                tags=["romanian_basics", "a_fi_present"],
                hint="Use the present tense.",
            )
        ],
    )
    service.lesson_repository.save("default-learner", broken_lesson)

    session = service.start_or_resume_lesson_session()

    assert session.lesson is not None
    assert session.lesson.lesson_id != "broken-lesson"


def test_start_or_resume_lesson_session_skips_saved_lesson_with_missing_sentence_context(tmp_path):
    service = build_learning_service(tmp_path)
    progress = service.get_or_create_user_progress()
    service.user_progress_repository.save(progress)
    broken_lesson = Lesson(
        lesson_id="broken-sentence-lesson",
        topic="romanian_basics",
        level=1,
        cefr_band=CEFRBand.A1,
        difficulty=2,
        explanation_text="Broken saved lesson.",
        example_sentences=[],
        key_rules=["Use a fi."],
        quiz_questions=[
            Question(
                question_id="q-broken-sentence",
                prompt="Complete the sentence with the correct form of a fi.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                difficulty_rating=2,
                cefr_band=CEFRBand.A1,
                correct_answer="este, suntem",
                explanation="Needs the actual sentence to be answerable.",
                tags=["romanian_basics", "a_fi_present"],
                options=["este, suntem", "sunt, sunt", "esti, sunteti", "suntem, este"],
                hint="Look at both subjects.",
            )
        ],
    )
    service.lesson_repository.save("default-learner", broken_lesson)

    session = service.start_or_resume_lesson_session()

    assert session.lesson is not None
    assert session.lesson.lesson_id != "broken-sentence-lesson"


def test_correctly_answered_questions_are_excluded_for_next_five_question_sets(tmp_path):
    service = build_learning_service(tmp_path)
    storage = SQLiteStorage(tmp_path / "lumina_romana.db")
    storage.initialize()
    offline_repository = SQLiteOfflineQuestionRepository(storage)
    offline_repository.upsert_questions(
        "romanian_basics",
        [build_offline_question("romanian_basics", index) for index in range(1, 31)],
    )

    first_session = service.start_topic_lesson("romanian_basics")
    assert first_session.lesson is not None
    first_prompts = {question.prompt for question in first_session.lesson.quiz_questions}
    first_answers = {
        question.question_id: question.correct_answer
        for question in first_session.lesson.quiz_questions
    }
    service.submit_quiz(first_session.lesson.lesson_id, first_answers)

    future_prompts: set[str] = set()
    for _ in range(5):
        lesson_session = service.start_topic_lesson("romanian_basics")
        assert lesson_session.lesson is not None
        future_prompts.update(question.prompt for question in lesson_session.lesson.quiz_questions)
        service.submit_quiz(
            lesson_session.lesson.lesson_id,
            {question.question_id: "" for question in lesson_session.lesson.quiz_questions},
        )

    assert not (first_prompts & future_prompts)
