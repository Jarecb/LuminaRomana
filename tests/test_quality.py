from __future__ import annotations

import json
import logging
from pathlib import Path

from app.ai import AIProviderResponse, AIService, LessonGenerationRequest, PromptBuilder, TransientAIError
from app.ai.providers import DisabledAIProvider
from app.models import CEFRBand, UserProgress
from app.services import ContentLibrary, DifficultyManager, QualityService
from app.storage import SQLiteOfflineQuestionRepository, SQLiteStorage
from app.validation import ContentValidator

from tests.test_ai import CountingQuotaProvider, StubProvider


def test_quality_service_samples_requested_topics(tmp_path):
    storage = SQLiteStorage(tmp_path / "lumina_romana.db")
    storage.initialize()
    offline_repository = SQLiteOfflineQuestionRepository(storage)
    content_library = ContentLibrary(offline_question_repository=offline_repository)
    ai_service = AIService(
        provider=DisabledAIProvider(),
        prompt_builder=PromptBuilder(),
        content_library=content_library,
        difficulty_manager=DifficultyManager(content_library),
        content_validator=ContentValidator(),
        logger=logging.getLogger("test.quality"),
        max_retries=1,
        offline_question_repository=offline_repository,
    )
    quality_service = QualityService(
        content_library=content_library,
        ai_service=ai_service,
        offline_question_repository=offline_repository,
    )

    report = quality_service.sample_lessons(
        topic_ids=("romanian_basics", "b2_core_structures"),
        question_count=5,
    )

    assert report.total_samples == 2
    assert report.fallback_samples == 2
    assert report.ai_samples == 0
    assert report.samples[0].topic_id == "romanian_basics"
    assert len(report.samples[0].question_types) == 5
    assert any(question_type == "guided_writing" for question_type in report.samples[1].question_types)


def test_quality_service_seeds_offline_questions_for_requested_topics(tmp_path):
    storage = SQLiteStorage(tmp_path / "lumina_romana.db")
    storage.initialize()
    offline_repository = SQLiteOfflineQuestionRepository(storage)
    content_library = ContentLibrary(offline_question_repository=offline_repository)
    ai_service = AIService(
        provider=DisabledAIProvider(),
        prompt_builder=PromptBuilder(),
        content_library=content_library,
        difficulty_manager=DifficultyManager(content_library),
        content_validator=ContentValidator(),
        logger=logging.getLogger("test.quality.seed"),
        max_retries=1,
        offline_question_repository=offline_repository,
    )
    quality_service = QualityService(
        content_library=content_library,
        ai_service=ai_service,
        offline_question_repository=offline_repository,
    )

    report = quality_service.seed_offline_question_bank(
        topic_ids=("romanian_basics",),
        question_count=10,
    )

    assert report.total_topics == 1
    assert report.total_questions_after == offline_repository.count_all()
    assert report.topics[0].topic_id == "romanian_basics"
    assert report.topics[0].stored_question_count_after == offline_repository.count_for_topic("romanian_basics")
    assert report.topics[0].stored_question_count_after >= 1
    assert report.topics[0].warnings


def test_ai_service_metrics_capture_retries_validation_failures_and_fallback():
    provider = StubProvider(
        responses=[
            TransientAIError("temporary timeout"),
            AIProviderResponse(
                provider_name="stub",
                model="stub-model",
                content='{"lesson_id":"bad","topic":"present_tense_verbs","level":4,"cefr_band":"A1","difficulty":4,"explanation_text":"Bad.","example_sentences":[{"romanian":"Eu dragon.","english":"I dragon."}],"key_rules":["Use anything."],"quiz_questions":[{"question_id":"q1","type":"multiple_choice","prompt":"Pick one.","options":["merg","merge"],"correct_answer":"merge","explanation":"","difficulty":4,"tags":["nouns_and_articles"],"hint":"guess","rubric":{},"cefr_band":"A1"},{"question_id":"q2","type":"multiple_choice","prompt":"Pick two.","options":["merg","merge"],"correct_answer":"merge","explanation":"","difficulty":4,"tags":["nouns_and_articles"],"hint":"guess","rubric":{},"cefr_band":"A1"},{"question_id":"q3","type":"multiple_choice","prompt":"Pick three.","options":["merg","merge"],"correct_answer":"merge","explanation":"","difficulty":4,"tags":["nouns_and_articles"],"hint":"guess","rubric":{},"cefr_band":"A1"},{"question_id":"q4","type":"multiple_choice","prompt":"Pick four.","options":["merg","merge"],"correct_answer":"merge","explanation":"","difficulty":4,"tags":["nouns_and_articles"],"hint":"guess","rubric":{},"cefr_band":"A1"},{"question_id":"q5","type":"multiple_choice","prompt":"Pick five.","options":["merg","merge"],"correct_answer":"merge","explanation":"","difficulty":4,"tags":["nouns_and_articles"],"hint":"guess","rubric":{},"cefr_band":"A1"}]}',
            ),
        ]
    )
    content_library = ContentLibrary()
    service = AIService(
        provider=provider,
        prompt_builder=PromptBuilder(),
        content_library=content_library,
        difficulty_manager=DifficultyManager(content_library),
        content_validator=ContentValidator(),
        logger=logging.getLogger("test.quality.metrics"),
        max_retries=1,
    )

    result = service.generate_lesson(
        LessonGenerationRequest(
            user_progress=UserProgress(
                user_id="learner-1",
                current_level=4,
                current_cefr_band=CEFRBand.A1,
                current_difficulty=3,
            ),
            topic_id="present_tense_verbs",
        )
    )
    metrics = service.metrics_snapshot()

    assert result.source == "fallback"
    assert metrics.total_requests == 1
    assert metrics.transient_failures == 1
    assert metrics.validation_failures == 1
    assert metrics.retries_attempted == 2
    assert metrics.fallback_generations == 1


def test_prompt_regression_fixtures_match_current_builder():
    fixture_path = Path(__file__).parent / "fixtures" / "prompt_regression_cases.json"
    fixture_cases = json.loads(fixture_path.read_text(encoding="utf-8"))
    content_library = ContentLibrary()
    difficulty_manager = DifficultyManager(content_library)
    builder = PromptBuilder()

    for case in fixture_cases:
        progress = UserProgress(
            user_id="fixture-user",
            current_level=case["progress"]["current_level"],
            current_cefr_band=CEFRBand(case["progress"]["current_cefr_band"]),
            current_difficulty=case["progress"]["current_difficulty"],
            recent_scores=list(case["progress"].get("recent_scores", [])),
            mastery_matrix=dict(case["progress"].get("mastery_matrix", {})),
            skill_scores=dict(case["progress"].get("skill_scores", {})),
        )
        topic = content_library.get_topic(case["topic_id"])
        assert topic is not None
        assessment = difficulty_manager.assess_user(progress)
        constraints = difficulty_manager.build_prompt_constraints(
            user_progress=progress,
            assessment=assessment,
            focus_tags=tuple(case["focus_tags"]),
            topic_id=topic.topic_id,
        )
        prompt = builder.build_lesson_prompt(
            request=LessonGenerationRequest(
                user_progress=progress,
                topic_id=topic.topic_id,
                session_goal=case["session_goal"],
                focus_tags=tuple(case["focus_tags"]),
                question_count=case["question_count"],
            ),
            topic=topic,
            assessment=assessment,
            constraints=constraints,
        )

        for key, value in case["expected_metadata"].items():
            assert prompt.metadata[key] == value
        combined = "\n".join(message.content for message in prompt.messages)
        for snippet in case["required_snippets"]:
            assert snippet in combined


def test_quality_service_stops_seed_loop_after_quota_exhaustion(tmp_path):
    storage = SQLiteStorage(tmp_path / "lumina_romana.db")
    storage.initialize()
    offline_repository = SQLiteOfflineQuestionRepository(storage)
    content_library = ContentLibrary(offline_question_repository=offline_repository)
    ai_service = AIService(
        provider=CountingQuotaProvider(),
        prompt_builder=PromptBuilder(),
        content_library=content_library,
        difficulty_manager=DifficultyManager(content_library),
        content_validator=ContentValidator(),
        logger=logging.getLogger("test.quality.quota"),
        max_retries=2,
        offline_question_repository=offline_repository,
    )
    quality_service = QualityService(
        content_library=content_library,
        ai_service=ai_service,
        offline_question_repository=offline_repository,
    )

    report = quality_service.seed_offline_question_bank(
        topic_ids=("romanian_basics",),
        question_count=100,
    )
    metrics = ai_service.metrics_snapshot()

    assert report.topics[0].topic_id == "romanian_basics"
    assert any("quota exhaustion" in warning.casefold() for warning in report.topics[0].warnings)
    assert metrics.fallback_generations == 1
