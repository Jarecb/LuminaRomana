from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.ai.types import LessonGenerationRequest
from app.models import CEFRBand, QuestionType, TopicMetadata, UserProgress

from .roadmap import ContentLibrary

if TYPE_CHECKING:
    from app.ai.service import AIService


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


@dataclass(slots=True)
class QualityService:
    content_library: ContentLibrary
    ai_service: "AIService"

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
