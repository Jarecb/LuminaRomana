import json
import logging
from urllib import request as urllib_request

import pytest

from app.ai import (
    AIMessage,
    AIProviderResponse,
    AIService,
    LessonGenerationError,
    LessonGenerationRequest,
    PromptBuilder,
    QuotaExceededAIError,
    TransientAIError,
)
from app.ai.providers import BaseAIProvider
from app.models import CEFRBand, UserProgress
from app.services import ContentLibrary, DifficultyManager
from app.storage import SQLiteOfflineQuestionRepository, SQLiteStorage
from app.validation import ContentValidator, lesson_to_payload


class StubProvider(BaseAIProvider):
    def __init__(self, responses):
        self.provider_name = "stub"
        self.model = "stub-model"
        self._responses = list(responses)

    @property
    def is_configured(self) -> bool:
        return True

    def generate_json(self, messages, temperature):
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class CountingQuotaProvider(BaseAIProvider):
    def __init__(self):
        self.provider_name = "quota-stub"
        self.model = "quota-model"
        self.calls = 0

    @property
    def is_configured(self) -> bool:
        return True

    def generate_json(self, messages, temperature):
        self.calls += 1
        raise QuotaExceededAIError("Quota exhausted.", retry_after_seconds=60.0)


def test_prompt_builder_uses_topic_difficulty_cefr_and_focus_tags():
    content_library = ContentLibrary()
    difficulty_manager = DifficultyManager(content_library)
    builder = PromptBuilder()
    progress = UserProgress(
        user_id="learner-1",
        current_level=5,
        current_cefr_band=CEFRBand.A2,
        current_difficulty=4,
        recent_scores=[82.0, 91.0, 93.0],
        mastery_matrix={
            "romanian_basics": 0.95,
            "nouns_and_articles": 0.9,
            "core_cases": 0.84,
            "present_tense_verbs": 0.8,
        },
    )
    topic = content_library.get_topic("pronouns_and_tenses")
    assert topic is not None

    assessment = difficulty_manager.assess_user(progress)
    constraints = difficulty_manager.build_prompt_constraints(
        user_progress=progress,
        assessment=assessment,
        focus_tags=("feminine_endings", "object_pronouns"),
        topic_id=topic.topic_id,
    )

    prompt = builder.build_lesson_prompt(
        request=LessonGenerationRequest(
            user_progress=progress,
            topic_id=topic.topic_id,
            session_goal="lesson",
            focus_tags=("feminine_endings", "object_pronouns"),
            question_count=4,
        ),
        topic=topic,
        assessment=assessment,
        constraints=constraints,
    )

    assert prompt.metadata["topic_id"] == "pronouns_and_tenses"
    assert prompt.metadata["recommended_cefr_band"] == "A2"
    assert prompt.metadata["difficulty"] == 5
    assert prompt.metadata["focus_tags"] == ["feminine_endings", "object_pronouns"]
    assert "target CEFR band is A2" in prompt.messages[0].content
    assert "Recommended next difficulty from the adaptive engine: 5." in prompt.messages[1].content
    assert "Focus tags from recent learner errors: feminine_endings, object_pronouns." in prompt.messages[1].content
    assert "The top-level difficulty field is mandatory and must be an integer from 1 to 10." in prompt.messages[1].content
    assert "Write explanation_text, every key_rules item" in prompt.messages[1].content
    assert "Allowed question type values are exactly:" in prompt.messages[1].content
    assert "Length limits are strict: explanation_text <= 800 characters;" in prompt.messages[1].content
    assert "Every guided_writing rubric must have at least two named criteria" in prompt.messages[1].content


def test_ai_service_retries_transient_failures_and_returns_json(caplog):
    provider = StubProvider(
        responses=[
            TransientAIError("temporary timeout"),
            AIProviderResponse(
                provider_name="stub",
                model="stub-model",
                content="""
                {
                  "lesson_id": "lesson-1",
                  "topic": "present_tense_verbs",
                  "level": 4,
                  "cefr_band": "A1",
                  "difficulty": 4,
                  "explanation_text": "Romanian present tense verbs must agree with the subject in short daily sentences.",
                  "example_sentences": [
                    {"romanian": "Eu merg acasa.", "english": "I go home."}
                  ],
                  "key_rules": ["Match the verb ending to the subject."],
                  "quiz_questions": [
                    {
                      "question_id": "q1",
                      "type": "multiple_choice",
                      "prompt": "Choose the correct form: Noi ___ acasa.",
                      "options": ["merge", "merg", "mergem", "mergeti"],
                      "correct_answer": "mergem",
                      "explanation": "The subject 'noi' takes the first-person plural form 'mergem'.",
                      "difficulty": 4,
                      "tags": ["present_tense_verbs", "agreement"],
                      "hint": "Use the form for 'we'.",
                      "rubric": {},
                      "cefr_band": "A1"
                    },
                    {
                      "question_id": "q2",
                      "type": "multiple_choice",
                      "prompt": "Choose the correct form: Eu ___ romana.",
                      "options": ["invata", "invat", "invatam", "invatati"],
                      "correct_answer": "invat",
                      "explanation": "The subject 'eu' takes the first-person singular form 'invat'.",
                      "difficulty": 4,
                      "tags": ["present_tense_verbs", "present_tense"],
                      "hint": "Use the form for 'I'.",
                      "rubric": {},
                      "cefr_band": "A1"
                    },
                    {
                      "question_id": "q3",
                      "type": "multiple_choice",
                      "prompt": "Choose the correct form: Ei ___ astazi.",
                      "options": ["lucreaza", "lucrez", "lucram", "lucrati"],
                      "correct_answer": "lucreaza",
                      "explanation": "The subject 'ei' takes the third-person plural form here.",
                      "difficulty": 4,
                      "tags": ["present_tense_verbs", "present_tense"],
                      "hint": "Use the form for 'they'.",
                      "rubric": {},
                      "cefr_band": "A1"
                    },
                    {
                      "question_id": "q4",
                      "type": "multiple_choice",
                      "prompt": "Choose the correct form: Tu ___ mult.",
                      "options": ["citesti", "citesc", "citim", "citeste"],
                      "correct_answer": "citesti",
                      "explanation": "The subject 'tu' takes the second-person singular form 'citesti'.",
                      "difficulty": 4,
                      "tags": ["present_tense_verbs", "agreement"],
                      "hint": "Use the form for 'you' singular.",
                      "rubric": {},
                      "cefr_band": "A1"
                    },
                    {
                      "question_id": "q5",
                      "type": "multiple_choice",
                      "prompt": "Choose the correct form: Noi ___ acum.",
                      "options": ["scriem", "scriu", "scrie", "scrii"],
                      "correct_answer": "scriem",
                      "explanation": "The subject 'noi' takes the first-person plural form 'scriem'.",
                      "difficulty": 4,
                      "tags": ["present_tense_verbs", "agreement"],
                      "hint": "Use the form for 'we'.",
                      "rubric": {},
                      "cefr_band": "A1"
                    }
                  ]
                }
                """,
                finish_reason="stop",
                prompt_tokens=123,
                completion_tokens=45,
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
        logger=logging.getLogger("test.ai"),
        max_retries=2,
    )
    progress = UserProgress(
        user_id="learner-1",
        current_level=4,
        current_cefr_band=CEFRBand.A1,
        current_difficulty=3,
        recent_scores=[72.0, 80.0, 88.0],
        mastery_matrix={
            "romanian_basics": 0.95,
            "nouns_and_articles": 0.9,
            "core_cases": 0.8,
        },
    )

    with caplog.at_level(logging.INFO):
        result = service.generate_lesson(
            LessonGenerationRequest(
                user_progress=progress,
                topic_id="present_tense_verbs",
                session_goal="lesson",
                focus_tags=("agreement",),
            )
        )

    assert result.lesson_payload["lesson_id"] == "lesson-1"
    assert result.lesson_payload["topic"] == "present_tense_verbs"
    assert result.lesson.topic == "present_tense_verbs"
    assert result.attempts == 2
    assert result.source == "ai"
    assert "temporary timeout" in caplog.text
    assert "provider=stub" in caplog.text


def test_ai_service_falls_back_after_validation_failures():
    provider = StubProvider(
        responses=[
            AIProviderResponse(
                provider_name="stub",
                model="stub-model",
                content="""
                {
                  "lesson_id": "bad-lesson",
                  "topic": "present_tense_verbs",
                  "level": 4,
                  "cefr_band": "A1",
                  "difficulty": 3,
                  "explanation_text": "Bad scope lesson.",
                  "example_sentences": [{"romanian": "Eu dragon.", "english": "I dragon."}],
                  "key_rules": ["Use anything."],
                  "quiz_questions": [
                    {
                      "question_id": "q1",
                      "type": "multiple_choice",
                      "prompt": "Pick one.",
                      "options": ["merg", "merg"],
                      "correct_answer": "merge",
                      "explanation": "",
                      "difficulty": 3,
                      "tags": ["nouns_and_articles"],
                      "hint": "guess",
                      "rubric": {},
                      "cefr_band": "A1"
                    },
                    {
                      "question_id": "q2",
                      "type": "multiple_choice",
                      "prompt": "Pick one.",
                      "options": ["merg", "merge"],
                      "correct_answer": "merge",
                      "explanation": "",
                      "difficulty": 3,
                      "tags": ["nouns_and_articles"],
                      "hint": "guess",
                      "rubric": {},
                      "cefr_band": "A1"
                    },
                    {
                      "question_id": "q3",
                      "type": "multiple_choice",
                      "prompt": "Pick one.",
                      "options": ["merg", "merge"],
                      "correct_answer": "merge",
                      "explanation": "",
                      "difficulty": 3,
                      "tags": ["nouns_and_articles"],
                      "hint": "guess",
                      "rubric": {},
                      "cefr_band": "A1"
                    },
                    {
                      "question_id": "q4",
                      "type": "multiple_choice",
                      "prompt": "Pick one.",
                      "options": ["merg", "merge"],
                      "correct_answer": "merge",
                      "explanation": "",
                      "difficulty": 3,
                      "tags": ["nouns_and_articles"],
                      "hint": "guess",
                      "rubric": {},
                      "cefr_band": "A1"
                    },
                    {
                      "question_id": "q5",
                      "type": "multiple_choice",
                      "prompt": "Pick one.",
                      "options": ["merg", "merge"],
                      "correct_answer": "merge",
                      "explanation": "",
                      "difficulty": 3,
                      "tags": ["nouns_and_articles"],
                      "hint": "guess",
                      "rubric": {},
                      "cefr_band": "A1"
                    }
                  ]
                }
                """,
            ),
            AIProviderResponse(
                provider_name="stub",
                model="stub-model",
                content='{"lesson_id":"still-bad","topic":"present_tense_verbs","level":4,"cefr_band":"A1","difficulty":3,"explanation_text":"Bad.","example_sentences":[{"romanian":"Eu merg.","english":"I go."}],"key_rules":["Keep it simple."],"quiz_questions":[]}',  # noqa: E501
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
        logger=logging.getLogger("test.ai.fallback"),
        max_retries=1,
    )
    progress = UserProgress(user_id="learner-1", current_difficulty=3)

    result = service.generate_lesson(
        LessonGenerationRequest(
            user_progress=progress,
            topic_id="present_tense_verbs",
            question_count=5,
        )
    )

    assert result.source == "fallback"
    assert result.lesson.lesson_id.startswith("fallback-present_tense_verbs")
    assert result.lesson.topic == "present_tense_verbs"
    assert len(result.lesson.quiz_questions) == 5
    assert result.warnings


def test_ai_service_uses_fallback_when_provider_is_unconfigured():
    content_library = ContentLibrary()
    from app.ai.providers import DisabledAIProvider

    service = AIService(
        provider=DisabledAIProvider(),
        prompt_builder=PromptBuilder(),
        content_library=content_library,
        difficulty_manager=DifficultyManager(content_library),
        content_validator=ContentValidator(),
        logger=logging.getLogger("test.ai.disabled"),
        max_retries=1,
    )

    result = service.generate_lesson(
        LessonGenerationRequest(
            user_progress=UserProgress(user_id="learner-1"),
            topic_id="romanian_basics",
        )
    )

    assert result.source == "fallback"
    assert result.lesson.topic == "romanian_basics"


def test_ai_service_raises_for_unknown_topic():
    provider = StubProvider(responses=[TransientAIError("still failing"), TransientAIError("still failing")])
    content_library = ContentLibrary()
    service = AIService(
        provider=provider,
        prompt_builder=PromptBuilder(),
        content_library=content_library,
        difficulty_manager=DifficultyManager(content_library),
        content_validator=ContentValidator(),
        logger=logging.getLogger("test.ai.fail"),
        max_retries=1,
    )
    progress = UserProgress(user_id="learner-1")

    with pytest.raises(ValueError):
        service.generate_lesson(
            LessonGenerationRequest(
                user_progress=progress,
                topic_id="unknown_topic",
            )
        )


def test_ai_service_uses_b1_fallback_with_integrated_question_types():
    content_library = ContentLibrary()
    service = AIService(
        provider=StubProvider(responses=[TransientAIError("timeout"), TransientAIError("timeout")]),
        prompt_builder=PromptBuilder(),
        content_library=content_library,
        difficulty_manager=DifficultyManager(content_library),
        content_validator=ContentValidator(),
        logger=logging.getLogger("test.ai.b1"),
        max_retries=1,
    )
    progress = UserProgress(
        user_id="learner-1",
        current_level=7,
        current_cefr_band=CEFRBand.B1,
        current_difficulty=7,
        recent_scores=[84.0, 86.0, 88.0],
        mastery_matrix={
            "romanian_basics": 0.9,
            "nouns_and_articles": 0.9,
            "core_cases": 0.88,
            "present_tense_verbs": 0.86,
            "pronouns_and_tenses": 0.82,
            "connected_communication": 0.8,
        },
    )

    result = service.generate_lesson(
        LessonGenerationRequest(
            user_progress=progress,
            topic_id="narrative_b1_grammar",
            question_count=5,
        )
    )

    assert result.source == "fallback"
    assert result.lesson.cefr_band == CEFRBand.B1
    assert any(question.question_type.value == "sentence_transformation" for question in result.lesson.quiz_questions)
    assert any(question.question_type.value == "dialogue_completion" for question in result.lesson.quiz_questions)


def test_ai_service_uses_b2_fallback_with_reading_and_writing_tasks():
    content_library = ContentLibrary()
    service = AIService(
        provider=StubProvider(responses=[TransientAIError("timeout"), TransientAIError("timeout")]),
        prompt_builder=PromptBuilder(),
        content_library=content_library,
        difficulty_manager=DifficultyManager(content_library),
        content_validator=ContentValidator(),
        logger=logging.getLogger("test.ai.b2"),
        max_retries=1,
    )
    progress = UserProgress(
        user_id="learner-1",
        current_level=9,
        current_cefr_band=CEFRBand.B2,
        current_difficulty=9,
        recent_scores=[88.0, 90.0, 91.0],
        mastery_matrix={
            "romanian_basics": 0.9,
            "nouns_and_articles": 0.9,
            "core_cases": 0.88,
            "present_tense_verbs": 0.86,
            "pronouns_and_tenses": 0.84,
            "connected_communication": 0.83,
            "narrative_b1_grammar": 0.82,
            "b1_b2_transition": 0.81,
        },
        skill_scores={"reading": 84.0, "writing": 83.0, "integrated_grammar": 85.0},
    )

    result = service.generate_lesson(
        LessonGenerationRequest(
            user_progress=progress,
            topic_id="b2_core_structures",
            question_count=5,
        )
    )

    assert result.source == "fallback"
    assert result.lesson.cefr_band == CEFRBand.B2
    assert any(question.question_type.value == "reading_comprehension" for question in result.lesson.quiz_questions)
    assert any(question.question_type.value == "guided_writing" for question in result.lesson.quiz_questions)


def test_ai_service_archives_generated_questions_into_offline_pool(tmp_path):
    storage = SQLiteStorage(tmp_path / "lumina_romana.db")
    storage.initialize()
    offline_repository = SQLiteOfflineQuestionRepository(storage)
    content_library = ContentLibrary(offline_question_repository=offline_repository)
    difficulty_manager = DifficultyManager(content_library)
    archived_lesson = content_library.build_fallback_lesson("romanian_basics", difficulty=2, question_count=5)
    archived_lesson.lesson_id = "ai-lesson-1"
    archived_lesson.quiz_questions[0].question_id = "ai-q1"
    archived_lesson.quiz_questions[0].prompt = "AI archived prompt: Complete 'Eu ___ aici.'"

    service = AIService(
        provider=StubProvider(
            responses=[
                AIProviderResponse(
                    provider_name="gemini",
                    model="gemini-2.5-flash",
                    content=json.dumps(lesson_to_payload(archived_lesson)),
                )
            ]
        ),
        prompt_builder=PromptBuilder(),
        content_library=content_library,
        difficulty_manager=difficulty_manager,
        content_validator=ContentValidator(),
        logger=logging.getLogger("test.ai.archive"),
        max_retries=1,
        offline_question_repository=offline_repository,
    )

    result = service.generate_lesson(
        LessonGenerationRequest(
            user_progress=UserProgress(user_id="learner-1"),
            topic_id="romanian_basics",
            question_count=5,
        )
    )

    fallback_lesson = content_library.build_fallback_lesson("romanian_basics", difficulty=2, question_count=9)

    assert result.source == "ai"
    assert offline_repository.count_for_topic("romanian_basics") == 5
    assert any(
        question.prompt == "AI archived prompt: Complete 'Eu ___ aici.'"
        for question in fallback_lesson.quiz_questions
    )


def test_ai_service_skips_provider_calls_while_quota_cooldown_is_active():
    provider = CountingQuotaProvider()
    content_library = ContentLibrary()
    service = AIService(
        provider=provider,
        prompt_builder=PromptBuilder(),
        content_library=content_library,
        difficulty_manager=DifficultyManager(content_library),
        content_validator=ContentValidator(),
        logger=logging.getLogger("test.ai.quota"),
        max_retries=2,
    )

    first = service.generate_lesson(
        LessonGenerationRequest(
            user_progress=UserProgress(user_id="learner-1"),
            topic_id="romanian_basics",
        )
    )
    second = service.generate_lesson(
        LessonGenerationRequest(
            user_progress=UserProgress(user_id="learner-1"),
            topic_id="nouns_and_articles",
        )
    )

    assert first.source == "fallback"
    assert second.source == "fallback"
    assert provider.calls == 1
    assert "quota exhaustion" in second.warnings[0].casefold()


def test_ai_service_normalizes_empty_rubrics_before_validation():
    provider = StubProvider(
        responses=[
            AIProviderResponse(
                provider_name="stub",
                model="stub-model",
                content=json.dumps(
                    {
                        "lesson_id": "lesson-1",
                        "topic": "present_tense_verbs",
                        "level": 4,
                        "cefr_band": "A1",
                        "difficulty": 4,
                        "explanation_text": "Romanian present tense verbs must agree with the subject.",
                        "example_sentences": [
                            {"romanian": "Eu merg acasa.", "english": "I go home."}
                        ],
                        "key_rules": ["Match the verb ending to the subject."],
                        "quiz_questions": [
                            {
                                "question_id": "q1",
                                "type": "multiple_choice",
                                "prompt": "Choose the correct form: Eu ___ acasa.",
                                "options": ["merge", "merg", "mergem", "mergeti"],
                                "correct_answer": "merg",
                                "explanation": "The subject 'eu' takes the first-person singular form 'merg'.",
                                "difficulty": 4,
                                "tags": "present_tense_verbs",
                                "hint": "",
                                "rubric": [],
                                "cefr_band": "A1",
                            }
                        ],
                    }
                ),
            )
        ]
    )
    content_library = ContentLibrary()
    service = AIService(
        provider=provider,
        prompt_builder=PromptBuilder(),
        content_library=content_library,
        difficulty_manager=DifficultyManager(content_library),
        content_validator=ContentValidator(),
        logger=logging.getLogger("test.ai.normalize"),
        max_retries=1,
    )

    result = service.generate_lesson(
        LessonGenerationRequest(
            user_progress=UserProgress(
                user_id="learner-1",
                current_level=4,
                current_cefr_band=CEFRBand.A1,
                current_difficulty=4,
            ),
            topic_id="present_tense_verbs",
            question_count=1,
        )
    )

    assert result.source == "ai"
    assert result.lesson.quiz_questions[0].rubric == {}
    assert result.lesson.quiz_questions[0].tags == ["present_tense_verbs"]
    assert result.lesson.quiz_questions[0].hint is None


def test_ai_service_normalizes_missing_difficulty_and_question_type_aliases():
    provider = StubProvider(
        responses=[
            AIProviderResponse(
                provider_name="stub",
                model="stub-model",
                content=json.dumps(
                    {
                        "lesson_id": "lesson-1",
                        "topic": "present_tense_verbs",
                        "level": "4",
                        "cefr_band": "a1",
                        "explanation_text": "Romanian present tense verbs must agree with the subject.",
                        "example_sentences": [
                            {"romanian": "Eu merg acasa.", "english": "I go home."}
                        ],
                        "key_rules": "Match the verb ending to the subject.",
                        "questions": [
                            {
                                "question_id": "q1",
                                "question_type": "multiple-choice",
                                "prompt": "Choose the correct form: Eu ___ acasa.",
                                "choices": ["merge", "merg", "mergem", "mergeti"],
                                "answer": "merg",
                                "explanation": "The subject 'eu' takes the first-person singular form 'merg'.",
                                "tags": "present_tense_verbs",
                                "hint": "",
                                "rubric": [],
                            }
                        ],
                    }
                ),
            )
        ]
    )
    content_library = ContentLibrary()
    service = AIService(
        provider=provider,
        prompt_builder=PromptBuilder(),
        content_library=content_library,
        difficulty_manager=DifficultyManager(content_library),
        content_validator=ContentValidator(),
        logger=logging.getLogger("test.ai.normalize.aliases"),
        max_retries=1,
    )

    result = service.generate_lesson(
        LessonGenerationRequest(
            user_progress=UserProgress(
                user_id="learner-1",
                current_level=4,
                current_cefr_band=CEFRBand.A1,
                current_difficulty=4,
            ),
            topic_id="present_tense_verbs",
            question_count=1,
        )
    )

    assert result.source == "ai"
    assert result.lesson.difficulty == 4
    assert result.lesson.cefr_band == CEFRBand.A1
    assert result.lesson.quiz_questions[0].difficulty_rating == 4
    assert result.lesson.quiz_questions[0].question_type.value == "multiple_choice"
    assert result.lesson.quiz_questions[0].options == ["merge", "merg", "mergem", "mergeti"]


def test_ai_service_trims_overlong_text_fields_before_validation():
    provider = StubProvider(
        responses=[
            AIProviderResponse(
                provider_name="stub",
                model="stub-model",
                content=json.dumps(
                    {
                        "lesson_id": "lesson-1",
                        "topic": "present_tense_verbs",
                        "level": 4,
                        "cefr_band": "A1",
                        "difficulty": 4,
                        "explanation_text": "A" * 840,
                        "example_sentences": [
                            {
                                "romanian": "Eu merg acasa.",
                                "english": "B" * 220,
                            }
                        ],
                        "key_rules": ["Match the verb ending to the subject."],
                        "quiz_questions": [
                            {
                                "question_id": "q1",
                                "type": "multiple_choice",
                                "prompt": "C" * 340,
                                "options": ["merge", "merg", "mergem", "mergeti"],
                                "correct_answer": "merg",
                                "explanation": "D" * 520,
                                "difficulty": 4,
                                "tags": ["present_tense_verbs"],
                                "hint": "Keep it short.",
                                "rubric": {},
                                "cefr_band": "A1",
                            }
                        ],
                    }
                ),
            )
        ]
    )
    content_library = ContentLibrary()
    service = AIService(
        provider=provider,
        prompt_builder=PromptBuilder(),
        content_library=content_library,
        difficulty_manager=DifficultyManager(content_library),
        content_validator=ContentValidator(),
        logger=logging.getLogger("test.ai.normalize.lengths"),
        max_retries=1,
    )

    result = service.generate_lesson(
        LessonGenerationRequest(
            user_progress=UserProgress(
                user_id="learner-1",
                current_level=4,
                current_cefr_band=CEFRBand.A1,
                current_difficulty=4,
            ),
            topic_id="present_tense_verbs",
            question_count=1,
        )
    )

    assert result.source == "ai"
    assert len(result.lesson.explanation_text) <= 800
    assert len(result.lesson.example_sentences[0].english) <= 180
    assert len(result.lesson.quiz_questions[0].prompt) <= 320
    assert len(result.lesson.quiz_questions[0].explanation) <= 500


def test_gemini_provider_uses_system_instruction_and_json_mime_type(monkeypatch):
    captured = {}

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": '{"lesson_id":"l1","topic":"nouns_and_articles","level":2,"cefr_band":"A1","difficulty":2,"explanation_text":"x","example_sentences":[{"romanian":"Cartea este aici.","english":"The book is here."}],"key_rules":["x"],"quiz_questions":[{"question_id":"q1","type":"multiple_choice","prompt":"Choose the correct form: Cartea ___ aici.","options":["este","sunt"],"correct_answer":"este","explanation":"x","difficulty":2,"tags":["nouns_and_articles"],"hint":"x","rubric":{},"cefr_band":"A1"}]}'
                                    }
                                ]
                            },
                            "finishReason": "STOP",
                        }
                    ],
                    "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1},
                }
            ).encode("utf-8")

    def fake_urlopen(http_request, timeout):
        captured["url"] = http_request.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(http_request.data.decode("utf-8"))
        return DummyResponse()

    monkeypatch.setattr(urllib_request, "urlopen", fake_urlopen)

    from app.ai.providers import GeminiAIProvider

    provider = GeminiAIProvider(api_key="test-key", model="gemini-2.5-flash")
    response = provider.generate_json(
        messages=(
            AIMessage(role="system", content="System rules for nouns_and_articles."),
            AIMessage(role="user", content="Generate a lesson for nouns_and_articles."),
        ),
        temperature=0.2,
    )

    assert "/models/gemini-2.5-flash:generateContent?key=test-key" in captured["url"]
    assert captured["body"]["generationConfig"]["responseMimeType"] == "application/json"
    assert captured["body"]["system_instruction"]["parts"][0]["text"] == "System rules for nouns_and_articles."
    assert captured["body"]["contents"][0]["parts"][0]["text"] == "Generate a lesson for nouns_and_articles."
    assert "romanian_basics" not in json.dumps(captured["body"])
    assert response.provider_name == "gemini"


def test_ai_service_falls_back_when_guidance_text_is_in_romanian():
    provider = StubProvider(
        responses=[
            AIProviderResponse(
                provider_name="stub",
                model="stub-model",
                content=json.dumps(
                    {
                        "lesson_id": "lesson-language-bad",
                        "topic": "nouns_and_articles",
                        "level": 2,
                        "cefr_band": "A1",
                        "difficulty": 2,
                        "explanation_text": "In limba romana, substantivele primesc articole definite si nehotarate.",
                        "example_sentences": [
                            {
                                "romanian": "Cartea este pe masa.",
                                "english": "Cartea este pe masa si eu o caut acum.",
                            }
                        ],
                        "key_rules": ["Articolele definite se ataseaza la sfarsitul substantivului."],
                        "quiz_questions": [
                            {
                                "question_id": "q1",
                                "type": "multiple_choice",
                                "prompt": "Alege forma corecta: baiat ___ aici.",
                                "options": ["ul", "a"],
                                "correct_answer": "ul",
                                "explanation": "Forma corecta foloseste articolul hotarat.",
                                "difficulty": 2,
                                "tags": ["nouns_and_articles"],
                                "hint": "Gandeste-te la forma definita.",
                                "rubric": {},
                                "cefr_band": "A1",
                            }
                        ],
                    }
                ),
            )
        ]
    )
    content_library = ContentLibrary()
    service = AIService(
        provider=provider,
        prompt_builder=PromptBuilder(),
        content_library=content_library,
        difficulty_manager=DifficultyManager(content_library),
        content_validator=ContentValidator(),
        logger=logging.getLogger("test.ai.language"),
        max_retries=0,
    )

    result = service.generate_lesson(
        LessonGenerationRequest(
            user_progress=UserProgress(
                user_id="learner-1",
                current_level=2,
                current_cefr_band=CEFRBand.A1,
                current_difficulty=2,
            ),
            topic_id="nouns_and_articles",
            question_count=1,
        )
    )

    assert result.source == "fallback"
    assert "definite article" in result.lesson.explanation_text
    assert "noun" in result.lesson.explanation_text


def test_gemini_provider_treats_connection_reset_as_transient(monkeypatch):
    def fake_urlopen(http_request, timeout):
        raise ConnectionResetError("connection reset by peer")

    monkeypatch.setattr(urllib_request, "urlopen", fake_urlopen)

    from app.ai.providers import GeminiAIProvider

    provider = GeminiAIProvider(api_key="test-key", model="gemini-2.5-flash")

    with pytest.raises(TransientAIError) as exc_info:
        provider.generate_json(
            messages=(AIMessage(role="user", content="Generate valid JSON."),),
            temperature=0.2,
        )

    assert "connection reset by peer" in str(exc_info.value)
