from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.ai.types import LessonGenerationRequest
from app.models import CEFRBand, QuestionType, TopicMetadata, UserProgress

from .roadmap import ContentLibrary

if TYPE_CHECKING:
    from app.ai.service import AIService
    from app.storage.interfaces import OfflineQuestionRepository


@dataclass(frozen=True, slots=True)
class ContentSample:
    topic_id: str
    title: str
    level: int
    cefr_band: str
    source: str
    question_types: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ContentQualityReport:
    samples: tuple[ContentSample, ...]
    total_samples: int
    fallback_samples: int
    ai_samples: int


@dataclass(frozen=True, slots=True)
class OfflineQuestionSeedResult:
    topic_id: str
    title: str
    level: int
    cefr_band: str
    source: str
    requested_question_count: int
    stored_question_count_before: int
    stored_question_count_after: int
    added_question_count: int
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OfflineQuestionSeedReport:
    topics: tuple[OfflineQuestionSeedResult, ...]
    total_topics: int
    total_questions_before: int
    total_questions_after: int
    total_questions_added: int


@dataclass(slots=True)
class QualityService:
    content_library: ContentLibrary
    ai_service: "AIService"
    offline_question_repository: "OfflineQuestionRepository"

    def sample_lessons(
        self,
        *,
        topic_ids: Sequence[str] | None = None,
        question_count: int = 5,
        session_goal: str = "lesson",
    ) -> ContentQualityReport:
        selected_topics = self._resolve_topics(topic_ids)
        samples: list[ContentSample] = []
        fallback_samples = 0
        ai_samples = 0
        for topic in selected_topics:
            progress = self._sample_progress_for_topic(topic)
            result = self.ai_service.generate_lesson(
                LessonGenerationRequest(
                    user_progress=progress,
                    topic_id=topic.topic_id,
                    session_goal=session_goal,
                    question_count=question_count,
                )
            )
            if result.source == "fallback":
                fallback_samples += 1
            else:
                ai_samples += 1
            samples.append(
                ContentSample(
                    topic_id=topic.topic_id,
                    title=topic.title,
                    level=topic.level,
                    cefr_band=topic.cefr_band.value,
                    source=result.source,
                    question_types=tuple(question.question_type.value for question in result.lesson.quiz_questions),
                    warnings=result.warnings,
                )
            )
        return ContentQualityReport(
            samples=tuple(samples),
            total_samples=len(samples),
            fallback_samples=fallback_samples,
            ai_samples=ai_samples,
        )

    def seed_offline_question_bank(
        self,
        *,
        topic_ids: Sequence[str] | None = None,
        question_count: int = 10,
        session_goal: str = "lesson",
    ) -> OfflineQuestionSeedReport:
        selected_topics = self._resolve_topics(topic_ids)
        total_before = self.offline_question_repository.count_all()
        topic_results: list[OfflineQuestionSeedResult] = []
        max_seed_attempts_per_topic = 3

        for topic in selected_topics:
            before_count = self.offline_question_repository.count_for_topic(topic.topic_id)
            after_count = before_count
            source_labels: list[str] = []
            warnings: list[str] = []

            if after_count < question_count:
                progress = self._sample_progress_for_topic(topic)
                for _ in range(max_seed_attempts_per_topic):
                    remaining = question_count - after_count
                    result = self.ai_service.generate_lesson(
                        LessonGenerationRequest(
                            user_progress=progress,
                            topic_id=topic.topic_id,
                            session_goal=session_goal,
                            question_count=remaining,
                        )
                    )
                    self.offline_question_repository.upsert_questions(
                        topic.topic_id,
                        result.lesson.quiz_questions,
                        provider_name=result.provider_name,
                        model=result.model,
                    )
                    source_labels.append(result.source)
                    warnings.extend(result.warnings)
                    updated_count = self.offline_question_repository.count_for_topic(topic.topic_id)
                    if updated_count <= after_count and result.source == "fallback":
                        warnings.append(
                            "Stopped early because only deterministic fallback questions were available for this topic."
                        )
                        after_count = updated_count
                        break
                    after_count = updated_count
                    if after_count >= question_count:
                        break

            if after_count < question_count:
                warnings.append(
                    f"Stored {after_count} unique questions for this topic; the requested minimum was {question_count}."
                )

            topic_results.append(
                OfflineQuestionSeedResult(
                    topic_id=topic.topic_id,
                    title=topic.title,
                    level=topic.level,
                    cefr_band=topic.cefr_band.value,
                    source=self._summarize_seed_sources(before_count, source_labels),
                    requested_question_count=question_count,
                    stored_question_count_before=before_count,
                    stored_question_count_after=after_count,
                    added_question_count=after_count - before_count,
                    warnings=tuple(dict.fromkeys(warnings)),
                )
            )

        total_after = self.offline_question_repository.count_all()
        return OfflineQuestionSeedReport(
            topics=tuple(topic_results),
            total_topics=len(topic_results),
            total_questions_before=total_before,
            total_questions_after=total_after,
            total_questions_added=total_after - total_before,
        )

    def _resolve_topics(self, topic_ids: Sequence[str] | None) -> tuple[TopicMetadata, ...]:
        if not topic_ids:
            return self.content_library.all_topics()
        topics: list[TopicMetadata] = []
        for topic_id in topic_ids:
            topic = self.content_library.get_topic(topic_id)
            if topic is None:
                raise ValueError(f"Unknown topic '{topic_id}'.")
            topics.append(topic)
        return tuple(topics)

    def _sample_progress_for_topic(self, topic: TopicMetadata) -> UserProgress:
        progress = UserProgress(
            user_id=f"sampler-{topic.topic_id}",
            current_level=topic.level,
            current_cefr_band=topic.cefr_band,
            current_difficulty=max(1, min(10, topic.level)),
            recent_scores=[78.0, 84.0, 88.0] if topic.cefr_band in {CEFRBand.B1, CEFRBand.B2} else [72.0, 80.0, 85.0],
        )
        for candidate in self.content_library.all_topics():
            if candidate.level < topic.level:
                progress.update_mastery(candidate.topic_id, 0.82)
        if topic.cefr_band == CEFRBand.B2:
            progress.update_skill_score("grammar", 84.0)
            progress.update_skill_score("integrated_grammar", 82.0)
            progress.update_skill_score("reading", 83.0)
            progress.update_skill_score("writing", 81.0)
        elif topic.cefr_band == CEFRBand.B1:
            progress.update_skill_score("grammar", 80.0)
            progress.update_skill_score("integrated_grammar", 78.0)
        return progress

    def _summarize_seed_sources(self, existing_count: int, source_labels: Sequence[str]) -> str:
        if existing_count > 0 and not source_labels:
            return "existing"
        unique_sources = tuple(dict.fromkeys(source_labels))
        if not unique_sources:
            return "none"
        if len(unique_sources) == 1:
            return unique_sources[0]
        return "mixed"
