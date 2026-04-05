from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, replace
from typing import Any, Sequence

from app.ai.prompts import PromptBuilder
from app.ai.providers import BaseAIProvider, DisabledAIProvider
from app.ai.types import (
    AIConfigurationError,
    AIProviderError,
    LessonGenerationError,
    LessonGenerationRequest,
    LessonGenerationResult,
    QuotaExceededAIError,
    TransientAIError,
)
from app.services.difficulty import DifficultyManager
from app.services.roadmap import ContentLibrary
from app.storage.interfaces import OfflineQuestionRepository
from app.validation import ContentValidationError, ContentValidator, lesson_to_payload


@dataclass(frozen=True, slots=True)
class AIServiceMetricsSnapshot:
    total_requests: int
    successful_generations: int
    fallback_generations: int
    validation_failures: int
    retries_attempted: int
    transient_failures: int
    provider_failures: int
    json_parse_failures: int


TEXT_LIMITS = {
    "explanation_text": 800,
    "example_sentence": 180,
    "question_prompt": 320,
    "question_explanation": 500,
}


class AIService:
    def __init__(
            self,
            prompt_builder: PromptBuilder,
            content_library: ContentLibrary,
            difficulty_manager: DifficultyManager,
            content_validator: ContentValidator,
            logger: logging.Logger,
            providers: Sequence[BaseAIProvider] | None = None,
            max_retries_per_provider: int = 2,
            provider: BaseAIProvider | None = None,
            max_retries: int | None = None,
            offline_question_repository: OfflineQuestionRepository | None = None,
    ) -> None:
        if provider is not None and providers is not None:
            raise ValueError("Pass either provider or providers, not both.")
        resolved_providers = tuple(providers or (() if provider is None else (provider,)))
        if max_retries is not None:
            max_retries_per_provider = max_retries

        self._all_providers = resolved_providers
        self.providers = [p for p in resolved_providers if p.is_configured]
        self.prompt_builder = prompt_builder
        self.content_library = content_library
        self.difficulty_manager = difficulty_manager
        self.content_validator = content_validator
        self.logger = logger
        self.offline_question_repository = offline_question_repository
        self.max_retries = max(0, max_retries_per_provider)
        self._provider_cooldowns_until: dict[str, float] = {}
        self._provider_cooldown_reasons: dict[str, str] = {}
        self._metrics = {
            "total_requests": 0,
            "successful_generations": 0,
            "fallback_generations": 0,
            "validation_failures": 0,
            "retries_attempted": 0,
            "transient_failures": 0,
            "provider_failures": 0,
            "json_parse_failures": 0,
        }

    @property
    def is_configured(self) -> bool:
        return len(self.providers) > 0

    @property
    def provider(self) -> BaseAIProvider:
        if self.providers:
            return self.providers[0]
        if self._all_providers:
            return self._all_providers[0]
        return DisabledAIProvider()

    def metrics_snapshot(self) -> AIServiceMetricsSnapshot:
        return AIServiceMetricsSnapshot(**self._metrics)

    def generate_lesson(self, request: LessonGenerationRequest) -> LessonGenerationResult:
        try:
            topic = self.content_library.get_topic(request.topic_id)
            if topic is None:
                raise ValueError(f"Unknown topic '{request.topic_id}'.")

            if not self.providers:
                return self._trigger_fallback(request, None, "No AI providers are configured.")

            available_providers = [provider for provider in self.providers if self._provider_is_available(provider)]
            if not available_providers:
                return self._trigger_fallback(
                    request,
                    None,
                    self._provider_unavailable_reason_text() or "Configured AI providers are temporarily unavailable.",
                )

            self._metrics["total_requests"] += 1

            # Potential crash point: Difficulty Assessment
            assessment = self.difficulty_manager.assess_user(request.user_progress)
            constraints = self.difficulty_manager.build_prompt_constraints(
                user_progress=request.user_progress,
                assessment=assessment,
                focus_tags=request.focus_tags,
                topic_id=request.topic_id,
            )

            failure_reasons: list[str] = []

            for provider in available_providers:
                current_request = request
                max_attempts = self.max_retries + 1

                for attempt in range(1, max_attempts + 1):
                    prompt = self.prompt_builder.build_lesson_prompt(current_request, topic, assessment, constraints)

                    try:
                        response = provider.generate_json(prompt.messages, temperature=current_request.temperature)
                        payload = self._normalize_provider_payload(
                            json.loads(response.content),
                            default_difficulty=constraints.difficulty,
                            default_cefr_band=topic.cefr_band.value,
                        )

                        lesson = self.content_validator.validate_lesson_payload(
                            payload,
                            topic=topic,
                            expected_question_count=current_request.question_count,
                        )
                        self._archive_generated_questions(
                            topic_id=topic.topic_id,
                            lesson=lesson,
                            provider_name=response.provider_name,
                            model=response.model,
                        )

                        self._metrics["successful_generations"] += 1
                        return LessonGenerationResult(
                            lesson=lesson,
                            lesson_payload=lesson_to_payload(lesson),
                            provider_name=response.provider_name,
                            model=response.model,
                            prompt=prompt,
                            attempts=attempt,
                            source="ai",
                            finish_reason=response.finish_reason,
                            prompt_tokens=response.prompt_tokens,
                            completion_tokens=response.completion_tokens,
                        )

                    except QuotaExceededAIError as exc:
                        self._update_failure_metrics(exc)
                        self._mark_provider_cooldown(provider, exc)
                        error_msg = (
                            f"Provider quota exhausted via {provider.provider_name}: {str(exc)} "
                            f"(provider={provider.provider_name})"
                        )
                        self.logger.warning(error_msg)
                        failure_reasons.append(f"[{provider.provider_name}] {str(exc)}")
                        break

                    except (TransientAIError, json.JSONDecodeError, ContentValidationError) as exc:
                        error_msg = (
                            f"Attempt {attempt} via {provider.provider_name} failed: {str(exc)} "
                            f"(provider={provider.provider_name})"
                        )
                        self.logger.warning(error_msg)

                        self._update_failure_metrics(exc)
                        failure_reasons.append(f"[{provider.provider_name}] {str(exc)}")

                        if isinstance(exc, ContentValidationError):
                            feedback = tuple(
                                self._format_validation_feedback(issue)
                                for issue in exc.issues[:5]
                            )
                            current_request = replace(current_request, strict_validation=True,
                                                      validation_feedback=feedback)

                    except AIProviderError as exc:
                        self._metrics["provider_failures"] += 1
                        error_msg = f"Provider error via {provider.provider_name}: {str(exc)}"
                        self.logger.warning(error_msg)
                        failure_reasons.append(f"[{provider.provider_name}] {str(exc)}")
                        break

                    except Exception as exc:
                        self._metrics["provider_failures"] += 1
                        error_detail = f"Critical provider error ({provider.provider_name}): {str(exc)}"
                        self.logger.exception(error_detail)
                        failure_reasons.append(f"[{provider.provider_name}] Critical: {str(exc)}")
                        break

            return self._trigger_fallback(request, constraints, " | ".join(failure_reasons))

        except ValueError:
            raise
        except Exception as e:
            self.logger.exception("AIService crashed before provider execution: %s", e)
            return self._trigger_fallback(request, None, f"Pre-generation crash: {str(e)}")

    def _update_failure_metrics(self, exc: Exception) -> None:
        if isinstance(exc, QuotaExceededAIError):
            self._metrics["transient_failures"] += 1
            return
        self._metrics["retries_attempted"] += 1
        if isinstance(exc, TransientAIError):
            self._metrics["transient_failures"] += 1
        elif isinstance(exc, json.JSONDecodeError):
            self._metrics["json_parse_failures"] += 1
        elif isinstance(exc, ContentValidationError):
            self._metrics["validation_failures"] += 1

    def _trigger_fallback(self, request, constraints, reason_text) -> LessonGenerationResult:
        if self.content_library.supports_fallback(request.topic_id):
            self.logger.info("Falling back to local content library for topic: %s", request.topic_id)
            self._metrics["fallback_generations"] += 1
            fallback_difficulty = constraints.difficulty if constraints is not None else request.user_progress.current_difficulty

            fallback_lesson = self.content_library.build_fallback_lesson(
                request.topic_id,
                difficulty=fallback_difficulty,
                question_count=request.question_count,
                session_goal=request.session_goal,
                excluded_question_keys=request.excluded_question_keys,
            )
            return LessonGenerationResult(
                lesson=fallback_lesson,
                lesson_payload=lesson_to_payload(fallback_lesson),
                provider_name="fallback",
                model="deterministic",
                prompt=None,
                attempts=0,
                source="fallback",
                warnings=(f"AI failed. Reasons: {reason_text}",),
            )

        raise LessonGenerationError(f"Generation failed and no fallback available: {reason_text}")

    def _archive_generated_questions(
        self,
        *,
        topic_id: str,
        lesson,
        provider_name: str,
        model: str,
    ) -> None:
        if self.offline_question_repository is None:
            return
        try:
            self.offline_question_repository.upsert_questions(
                topic_id,
                lesson.quiz_questions,
                provider_name=provider_name,
                model=model,
            )
        except Exception:
            self.logger.warning(
                "Failed to archive AI-generated questions for topic %s.",
                topic_id,
                exc_info=True,
            )

    def _normalize_provider_payload(
        self,
        payload: Any,
        *,
        default_difficulty: int | None = None,
        default_cefr_band: str | None = None,
    ) -> Any:
        if not isinstance(payload, dict):
            return payload

        normalized_payload = dict(payload)
        if "quiz_questions" not in normalized_payload and isinstance(normalized_payload.get("questions"), list):
            normalized_payload["quiz_questions"] = normalized_payload["questions"]
        if "example_sentences" not in normalized_payload and isinstance(normalized_payload.get("examples"), list):
            normalized_payload["example_sentences"] = normalized_payload["examples"]
        if "difficulty" not in normalized_payload:
            if "difficulty_rating" in normalized_payload:
                normalized_payload["difficulty"] = normalized_payload["difficulty_rating"]
            elif default_difficulty is not None:
                normalized_payload["difficulty"] = default_difficulty
        if "key_rules" in normalized_payload and isinstance(normalized_payload["key_rules"], str):
            normalized_payload["key_rules"] = [normalized_payload["key_rules"]]
        if "difficulty" in normalized_payload:
            normalized_payload["difficulty"] = self._coerce_int(normalized_payload["difficulty"])
        if "level" in normalized_payload:
            normalized_payload["level"] = self._coerce_int(normalized_payload["level"])
        if "cefr_band" in normalized_payload:
            normalized_payload["cefr_band"] = self._normalize_cefr_band(normalized_payload["cefr_band"])
        if isinstance(normalized_payload.get("explanation_text"), str):
            normalized_payload["explanation_text"] = self._trim_text(
                normalized_payload["explanation_text"],
                TEXT_LIMITS["explanation_text"],
            )

        examples = normalized_payload.get("example_sentences")
        if isinstance(examples, list):
            normalized_examples = []
            for example in examples:
                if not isinstance(example, dict):
                    normalized_examples.append(example)
                    continue
                normalized_example = dict(example)
                if isinstance(normalized_example.get("romanian"), str):
                    normalized_example["romanian"] = self._trim_text(
                        normalized_example["romanian"],
                        TEXT_LIMITS["example_sentence"],
                    )
                if isinstance(normalized_example.get("english"), str):
                    normalized_example["english"] = self._trim_text(
                        normalized_example["english"],
                        TEXT_LIMITS["example_sentence"],
                    )
                normalized_examples.append(normalized_example)
            normalized_payload["example_sentences"] = normalized_examples

        quiz_questions = normalized_payload.get("quiz_questions")
        if not isinstance(quiz_questions, list):
            return normalized_payload

        lesson_difficulty = normalized_payload.get("difficulty")
        normalized_questions = []
        for raw_question in quiz_questions:
            if not isinstance(raw_question, dict):
                normalized_questions.append(raw_question)
                continue
            question = dict(raw_question)
            self._apply_missing_alias(question, "type", ("question_type",))
            self._apply_missing_alias(question, "options", ("choices",))
            self._apply_missing_alias(question, "correct_answer", ("answer", "reference_answer", "sample_answer"))
            self._apply_missing_alias(question, "difficulty", ("difficulty_rating",))
            self._apply_missing_alias(question, "cefr_band", ("cefr", "cefr_level"))
            if "difficulty" not in question and isinstance(lesson_difficulty, int):
                question["difficulty"] = lesson_difficulty
            if "difficulty" in question:
                question["difficulty"] = self._coerce_int(question["difficulty"])
            if "cefr_band" not in question and default_cefr_band is not None:
                question["cefr_band"] = default_cefr_band
            elif "cefr_band" in question:
                question["cefr_band"] = self._normalize_cefr_band(question["cefr_band"])
            if "type" in question:
                question["type"] = self._normalize_question_type(question["type"])
            if question.get("rubric") in (None, "", []):
                question["rubric"] = {}
            if question.get("options") is None:
                question["options"] = []
            if isinstance(question.get("tags"), str):
                question["tags"] = [question["tags"]]
            if question.get("hint") == "":
                question["hint"] = None
            if isinstance(question.get("prompt"), str):
                question["prompt"] = self._trim_text(question["prompt"], TEXT_LIMITS["question_prompt"])
            if isinstance(question.get("explanation"), str):
                question["explanation"] = self._trim_text(
                    question["explanation"],
                    TEXT_LIMITS["question_explanation"],
                )
            normalized_questions.append(question)

        normalized_payload["quiz_questions"] = normalized_questions
        return normalized_payload

    def _apply_missing_alias(self, payload: dict[str, Any], key: str, aliases: Sequence[str]) -> None:
        if key in payload:
            return
        for alias in aliases:
            if alias in payload:
                payload[key] = payload[alias]
                return

    def _coerce_int(self, value: Any) -> Any:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.isdigit():
                return int(stripped)
        return value

    def _normalize_cefr_band(self, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    def _normalize_question_type(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        normalized = value.strip().casefold().replace("-", "_").replace(" ", "_")
        while "__" in normalized:
            normalized = normalized.replace("__", "_")

        aliases = {
            "multiple_choice": "multiple_choice",
            "mcq": "multiple_choice",
            "english_to_romanian": "english_to_romanian_translation",
            "english_to_romanian_translation": "english_to_romanian_translation",
            "translate_to_romanian": "english_to_romanian_translation",
            "translation_to_romanian": "english_to_romanian_translation",
            "en_to_ro": "english_to_romanian_translation",
            "romanian_to_english": "romanian_to_english_translation",
            "romanian_to_english_translation": "romanian_to_english_translation",
            "translate_to_english": "romanian_to_english_translation",
            "translation_to_english": "romanian_to_english_translation",
            "ro_to_en": "romanian_to_english_translation",
            "fill_in_the_blank": "fill_in_the_blank",
            "fill_in_blank": "fill_in_the_blank",
            "fill_in_the_blanks": "fill_in_the_blank",
            "cloze": "fill_in_the_blank",
            "gap_fill": "fill_in_the_blank",
            "grammar_error_identification": "grammar_error_identification",
            "error_identification": "grammar_error_identification",
            "grammar_error": "grammar_error_identification",
            "sentence_transformation": "sentence_transformation",
            "sentence_rewrite": "sentence_transformation",
            "rewrite_sentence": "sentence_transformation",
            "guided_writing": "guided_writing",
            "guided_composition": "guided_writing",
            "writing_prompt": "guided_writing",
            "reading_comprehension": "reading_comprehension",
            "reading_task": "reading_comprehension",
            "dialogue_completion": "dialogue_completion",
            "complete_the_dialogue": "dialogue_completion",
            "conversation_completion": "dialogue_completion",
        }
        return aliases.get(normalized, normalized)

    def _trim_text(self, value: str, limit: int) -> str:
        stripped = value.strip()
        if len(stripped) <= limit:
            return stripped

        candidate = stripped[:limit].rstrip()
        boundary = max(
            candidate.rfind(". "),
            candidate.rfind("? "),
            candidate.rfind("! "),
            candidate.rfind("; "),
        )
        if boundary >= max(0, limit - 80):
            return candidate[: boundary + 1].rstrip()
        return candidate

    def _format_validation_feedback(self, issue) -> str:
        if "Text exceeds maximum length of" in issue.message:
            return f"{issue.path}: {issue.message}"
        return f"{issue.path}: {issue.message}"

    def _provider_is_available(self, provider: BaseAIProvider) -> bool:
        cooldown_until = self._provider_cooldowns_until.get(provider.provider_name)
        if cooldown_until is None:
            return True
        if time.monotonic() >= cooldown_until:
            self._provider_cooldowns_until.pop(provider.provider_name, None)
            self._provider_cooldown_reasons.pop(provider.provider_name, None)
            return True
        return False

    def _provider_unavailable_reason_text(self) -> str:
        if not self._provider_cooldown_reasons:
            return ""
        reasons = [self._provider_cooldown_reasons[name] for name in sorted(self._provider_cooldown_reasons)]
        return " | ".join(reasons)

    def _mark_provider_cooldown(self, provider: BaseAIProvider, exc: QuotaExceededAIError) -> None:
        retry_after_seconds = exc.retry_after_seconds if exc.retry_after_seconds is not None else 60.0
        retry_after_seconds = max(1.0, retry_after_seconds)
        self._provider_cooldowns_until[provider.provider_name] = time.monotonic() + retry_after_seconds
        retry_after_label = f"{retry_after_seconds:.0f}s"
        self._provider_cooldown_reasons[provider.provider_name] = (
            f"Provider {provider.provider_name} is temporarily unavailable due to quota exhaustion "
            f"(retry after about {retry_after_label})."
        )
