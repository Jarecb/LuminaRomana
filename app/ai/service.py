from __future__ import annotations

import json
import logging
import traceback
from dataclasses import dataclass, replace
from typing import Sequence

from app.ai.prompts import PromptBuilder
from app.ai.providers import BaseAIProvider, DisabledAIProvider
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
        # If this doesn't print, the crash is happening in the caller (main.py/cli.py/routes.py)
        print(f"\n[SERVICE] Entry point reached for topic: {request.topic_id}", flush=True)

        try:
            topic = self.content_library.get_topic(request.topic_id)
            if topic is None:
                print(f"[SERVICE] Error: Topic {request.topic_id} not found.", flush=True)
                raise ValueError(f"Unknown topic '{request.topic_id}'.")

            if not self.providers:
                print("[SERVICE] No configured providers found.", flush=True)
                return self._trigger_fallback(request, None, "No AI providers are configured.")

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

            for provider in self.providers:
                current_request = request
                max_attempts = self.max_retries + 1

                for attempt in range(1, max_attempts + 1):
                    print(f"[SERVICE] Calling {provider.provider_name} (Attempt {attempt})...", flush=True)
                    prompt = self.prompt_builder.build_lesson_prompt(current_request, topic, assessment, constraints)

                    try:
                        response = provider.generate_json(prompt.messages, temperature=current_request.temperature)
                        payload = json.loads(response.content)

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
                        print(f"[SERVICE] Success with {provider.provider_name}", flush=True)
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

                    except (TransientAIError, json.JSONDecodeError, ContentValidationError) as exc:
                        error_msg = (
                            f"Attempt {attempt} via {provider.provider_name} failed: {str(exc)} "
                            f"(provider={provider.provider_name})"
                        )
                        self.logger.warning(error_msg)
                        print(f"[SERVICE] {error_msg}", flush=True)

                        self._update_failure_metrics(exc)
                        failure_reasons.append(f"[{provider.provider_name}] {str(exc)}")

                        if isinstance(exc, ContentValidationError):
                            feedback = tuple(issue.message for issue in exc.issues[:5])
                            current_request = replace(current_request, strict_validation=True,
                                                      validation_feedback=feedback)

                    except Exception as exc:
                        self._metrics["provider_failures"] += 1
                        error_detail = f"Critical Provider Error ({provider.provider_name}): {str(exc)}"
                        print(f"[SERVICE] {error_detail}", flush=True)
                        traceback.print_exc()
                        failure_reasons.append(f"[{provider.provider_name}] Critical: {str(exc)}")
                        break

            return self._trigger_fallback(request, constraints, " | ".join(failure_reasons))

        except ValueError:
            raise
        except Exception as e:
            # THIS CATCHES EVERYTHING (DifficultyManager, etc.)
            print(f"\n[CRITICAL ERROR] AIService crashed before AI loop: {str(e)}", flush=True)
            traceback.print_exc()
            return self._trigger_fallback(request, None, f"Pre-generation crash: {str(e)}")

    def _update_failure_metrics(self, exc: Exception) -> None:
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
