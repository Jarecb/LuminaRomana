from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
import json
import logging

from app.ai.prompts import PromptBuilder
from app.ai.providers import BaseAIProvider
from app.ai.types import (
    AIConfigurationError,
    AIProviderError,
    LessonGenerationError,
    LessonGenerationRequest,
    LessonGenerationResult,
    TransientAIError,
)
from app.services.difficulty import DifficultyManager
from app.services.roadmap import ContentLibrary
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


class AIService:
    def __init__(
        self,
        provider: BaseAIProvider,
        prompt_builder: PromptBuilder,
        content_library: ContentLibrary,
        difficulty_manager: DifficultyManager,
        content_validator: ContentValidator,
        logger: logging.Logger,
        max_retries: int = 2,
    ) -> None:
        self.provider = provider
        self.prompt_builder = prompt_builder
        self.content_library = content_library
        self.difficulty_manager = difficulty_manager
        self.content_validator = content_validator
        self.logger = logger
        self.max_retries = max(0, max_retries)
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
        return self.provider.is_configured

    def metrics_snapshot(self) -> AIServiceMetricsSnapshot:
        return AIServiceMetricsSnapshot(**self._metrics)

    def generate_lesson(self, request: LessonGenerationRequest) -> LessonGenerationResult:
        topic = self.content_library.get_topic(request.topic_id)
        if topic is None:
            raise ValueError(f"Unknown topic '{request.topic_id}'.")
        self._metrics["total_requests"] += 1

        assessment = self.difficulty_manager.assess_user(request.user_progress)
        constraints = self.difficulty_manager.build_prompt_constraints(
            user_progress=request.user_progress,
            assessment=assessment,
            focus_tags=request.focus_tags,
            topic_id=request.topic_id,
        )

        max_attempts = self.max_retries + 1
        attempt_request = request
        failure_reasons: list[str] = []
        last_error: Exception | None = None
        attempts_used = 0
        for attempt in range(1, max_attempts + 1):
            attempts_used = attempt
            prompt = self.prompt_builder.build_lesson_prompt(attempt_request, topic, assessment, constraints)
            self.logger.info(
                "AI lesson request provider=%s model=%s attempt=%s topic=%s goal=%s difficulty=%s cefr=%s",
                self.provider.provider_name,
                self.provider.model,
                attempt,
                request.topic_id,
                request.session_goal,
                constraints.difficulty,
                constraints.cefr_band.value,
            )
            try:
                response = self.provider.generate_json(prompt.messages, temperature=attempt_request.temperature)
                payload = json.loads(response.content)
                if not isinstance(payload, dict):
                    raise AIProviderError("Provider returned JSON that was not an object.")
                lesson = self.content_validator.validate_lesson_payload(
                    payload,
                    topic=topic,
                    expected_question_count=attempt_request.question_count,
                )
                self.logger.info(
                    "AI lesson response provider=%s model=%s attempt=%s topic=%s finish_reason=%s prompt_tokens=%s completion_tokens=%s",
                    response.provider_name,
                    response.model,
                    attempt,
                    request.topic_id,
                    response.finish_reason,
                    response.prompt_tokens,
                    response.completion_tokens,
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
            except TransientAIError as exc:
                last_error = exc
                self._metrics["transient_failures"] += 1
                self._metrics["retries_attempted"] += 1
                self.logger.warning(
                    "AI transient failure provider=%s model=%s attempt=%s topic=%s error=%s",
                    self.provider.provider_name,
                    self.provider.model,
                    attempt,
                    request.topic_id,
                    exc,
                )
                failure_reasons.append(str(exc))
            except ContentValidationError as exc:
                last_error = exc
                self._metrics["validation_failures"] += 1
                self._metrics["retries_attempted"] += 1
                feedback = tuple(issue.message for issue in exc.issues[:5])
                self.logger.warning(
                    "AI content validation failed provider=%s model=%s attempt=%s topic=%s issues=%s",
                    self.provider.provider_name,
                    self.provider.model,
                    attempt,
                    request.topic_id,
                    " | ".join(f"{issue.path}: {issue.message}" for issue in exc.issues[:5]),
                )
                failure_reasons.extend(feedback)
                attempt_request = replace(
                    attempt_request,
                    strict_validation=True,
                    validation_feedback=feedback,
                )
            except AIConfigurationError as exc:
                last_error = exc
                self._metrics["provider_failures"] += 1
                self.logger.warning(
                    "AI is not configured for topic=%s error=%s",
                    request.topic_id,
                    exc,
                )
                failure_reasons.append(str(exc))
                break
            except json.JSONDecodeError as exc:
                last_error = exc
                self._metrics["json_parse_failures"] += 1
                self._metrics["retries_attempted"] += 1
                self.logger.error(
                    "AI response parsing failed provider=%s model=%s topic=%s attempt=%s error=%s",
                    self.provider.provider_name,
                    self.provider.model,
                    request.topic_id,
                    attempt,
                    exc,
                )
                failure_reasons.append("Provider response was not valid JSON.")
                attempt_request = replace(
                    attempt_request,
                    strict_validation=True,
                    validation_feedback=("Return valid JSON only with all required fields present.",),
                )
            except AIProviderError as exc:
                last_error = exc
                self._metrics["provider_failures"] += 1
                self._metrics["retries_attempted"] += 1
                self.logger.exception(
                    "AI provider failure provider=%s model=%s topic=%s attempt=%s",
                    self.provider.provider_name,
                    self.provider.model,
                    request.topic_id,
                    attempt,
                )
                failure_reasons.append(str(exc))

            if attempt >= max_attempts:
                break

        if self.content_library.supports_fallback(request.topic_id):
            fallback_lesson = self.content_library.build_fallback_lesson(
                request.topic_id,
                difficulty=constraints.difficulty,
                question_count=request.question_count,
                session_goal=request.session_goal,
            )
            warning = "AI generation fell back to deterministic template content."
            if failure_reasons:
                warning = f"{warning} Reasons: {' | '.join(failure_reasons[:3])}"
            self.logger.warning(
                "Lesson generation using fallback topic=%s attempts=%s reasons=%s",
                request.topic_id,
                attempts_used,
                " | ".join(failure_reasons[:5]) or "fallback requested",
            )
            self._metrics["fallback_generations"] += 1
            return LessonGenerationResult(
                lesson=fallback_lesson,
                lesson_payload=lesson_to_payload(fallback_lesson),
                provider_name=self.provider.provider_name,
                model=self.provider.model,
                prompt=self.prompt_builder.build_lesson_prompt(attempt_request, topic, assessment, constraints),
                attempts=attempts_used,
                source="fallback",
                warnings=(warning,),
            )

        if last_error is not None:
            raise LessonGenerationError(str(last_error)) from last_error
        raise LessonGenerationError("AI generation failed without a provider response.")
