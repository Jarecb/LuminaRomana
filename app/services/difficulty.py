"""Adaptive difficulty manager and prompt constraint builder.

Encapsulates logic to assess recent performance, recommend next difficulty, and
produce prompt constraints used when generating or selecting lesson content.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from app.models import CEFRBand, QuizAttempt, UserProgress
from app.services.roadmap import ContentLibrary


class SessionAction(StrEnum):
    ADVANCE = "advance"
    HOLD = "hold"
    REVIEW = "review"


@dataclass(frozen=True, slots=True)
class DifficultyAssessment:
    action: SessionAction
    current_difficulty: int
    next_difficulty: int
    latest_score: float | None
    recent_average_score: float | None
    recommended_cefr_band: CEFRBand
    review_required: bool


@dataclass(frozen=True, slots=True)
class PromptConstraints:
    difficulty: int
    cefr_band: CEFRBand
    session_goal: str
    vocabulary_profile: str
    sentence_profile: str
    scaffolding: str
    novelty: str
    include_hints: bool
    max_context_sentences: int
    focus_tags: tuple[str, ...]
    blocked_topics: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReviewSession:
    user_id: str
    difficulty: int
    cefr_band: CEFRBand
    recommended_topics: tuple[str, ...]
    focus_tags: tuple[str, ...]
    recheck_mastery_topics: tuple[str, ...]


@dataclass(slots=True)
class DifficultyManager:
    content_library: ContentLibrary
    target_score: float = 80.0
    performance_factor: float = 0.1
    mastery_threshold: float = 0.75
    b2_prerequisite_threshold: float = 0.8
    review_trigger_score: float = 60.0

    def assess_user(self, user_progress: UserProgress) -> DifficultyAssessment:
        latest_score = user_progress.recent_scores[-1] if user_progress.recent_scores else None
        recent_average = self.rolling_average(user_progress.recent_scores) if user_progress.recent_scores else None
        next_difficulty = self.calculate_next_difficulty(
            current_difficulty=user_progress.current_difficulty,
            recent_scores=user_progress.recent_scores,
        )
        review_required = latest_score is not None and latest_score < self.review_trigger_score
        if review_required:
            action = SessionAction.REVIEW
        elif next_difficulty > user_progress.current_difficulty:
            action = SessionAction.ADVANCE
        else:
            action = SessionAction.HOLD
        return DifficultyAssessment(
            action=action,
            current_difficulty=user_progress.current_difficulty,
            next_difficulty=next_difficulty,
            latest_score=latest_score,
            recent_average_score=recent_average,
            recommended_cefr_band=self.content_library.target_cefr_band(next_difficulty),
            review_required=review_required,
        )

    def rolling_average(self, recent_scores: Sequence[float]) -> float:
        if not recent_scores:
            raise ValueError("At least one score is required to calculate a rolling average.")
        window = list(recent_scores[-3:])
        return sum(window) / len(window)

    def calculate_next_difficulty(self, current_difficulty: int, recent_scores: Sequence[float]) -> int:
        if not 1 <= current_difficulty <= 10:
            raise ValueError("Current difficulty must be between 1 and 10.")
        if not recent_scores:
            return current_difficulty

        latest_score = recent_scores[-1]
        if latest_score < self.review_trigger_score:
            return max(1, current_difficulty - 1)

        rolling_average = self.rolling_average(recent_scores)
        formula_adjustment = round((rolling_average - self.target_score) * self.performance_factor)
        formula_adjustment = max(-1, min(1, formula_adjustment))

        if latest_score <= 85.0:
            adjustment = max(0, formula_adjustment)
        else:
            adjustment = max(1, formula_adjustment)

        return max(1, min(10, current_difficulty + adjustment))

    def topic_is_allowed(self, user_progress: UserProgress, topic_id: str) -> bool:
        return self.content_library.is_topic_unlocked(
            topic_id=topic_id,
            user_progress=user_progress,
            mastery_threshold=self.mastery_threshold,
            b2_prerequisite_threshold=self.b2_prerequisite_threshold,
        )

    def build_review_session(
        self,
        user_progress: UserProgress,
        attempts: Sequence[QuizAttempt],
        topic_id: str | None = None,
    ) -> ReviewSession:
        recent_attempts = list(attempts[-3:])
        mistake_counter: Counter[str] = Counter()
        for attempt in recent_attempts:
            mistake_counter.update(attempt.mistake_tags)

        focus_tags = tuple(tag for tag, _ in mistake_counter.most_common(3))
        recommended_topics = self._recommended_review_topics(user_progress, topic_id=topic_id)
        if not recommended_topics and topic_id is not None:
            recommended_topics = (topic_id,)

        assessment = self.assess_user(user_progress)
        return ReviewSession(
            user_id=user_progress.user_id,
            difficulty=max(1, assessment.next_difficulty),
            cefr_band=user_progress.current_cefr_band,
            recommended_topics=recommended_topics,
            focus_tags=focus_tags,
            recheck_mastery_topics=recommended_topics,
        )

    def build_prompt_constraints(
        self,
        user_progress: UserProgress,
        assessment: DifficultyAssessment | None = None,
        focus_tags: Sequence[str] = (),
        topic_id: str | None = None,
    ) -> PromptConstraints:
        assessment = assessment or self.assess_user(user_progress)
        blocked_topics = ()
        if topic_id is not None:
            blocked_topics = tuple(
                topic.topic_id
                for topic in self.content_library.blocking_topics_for_user(
                    topic_id=topic_id,
                    user_progress=user_progress,
                    mastery_threshold=self.mastery_threshold,
                    b2_prerequisite_threshold=self.b2_prerequisite_threshold,
                )
            )

        if assessment.review_required:
            vocabulary_profile = "simpler_vocabulary"
            sentence_profile = "short_sentences"
            scaffolding = "explicit_hints"
            novelty = "review_only"
            include_hints = True
        elif assessment.action is SessionAction.ADVANCE:
            vocabulary_profile = "broader_vocabulary"
            sentence_profile = "more_complex_syntax"
            scaffolding = "reduced_scaffolding"
            novelty = "guided_novelty"
            include_hints = False
        else:
            vocabulary_profile = "current_level_vocabulary"
            sentence_profile = "controlled_sentences"
            scaffolding = "light_scaffolding"
            novelty = "limited_novelty"
            include_hints = user_progress.current_cefr_band in {CEFRBand.A1, CEFRBand.A2}

        max_context_sentences = 1
        if user_progress.current_cefr_band in {CEFRBand.B1, CEFRBand.B2}:
            max_context_sentences = 2 if assessment.review_required else 3
        if assessment.recommended_cefr_band in {CEFRBand.B1, CEFRBand.B2}:
            context_score = self._context_score(user_progress)
            if assessment.review_required or context_score < 75.0:
                max_context_sentences = 2
            else:
                max_context_sentences = 4 if assessment.recommended_cefr_band == CEFRBand.B2 else 3

        return PromptConstraints(
            difficulty=assessment.next_difficulty,
            cefr_band=assessment.recommended_cefr_band,
            session_goal=assessment.action.value,
            vocabulary_profile=vocabulary_profile,
            sentence_profile=sentence_profile,
            scaffolding=scaffolding,
            novelty=novelty,
            include_hints=include_hints,
            max_context_sentences=max_context_sentences,
            focus_tags=tuple(dict.fromkeys(focus_tags)),
            blocked_topics=blocked_topics,
        )

    def _context_score(self, user_progress: UserProgress) -> float:
        values = [
            user_progress.skill_scores[skill_name]
            for skill_name in ("reading", "writing")
            if skill_name in user_progress.skill_scores
        ]
        if values:
            return sum(values) / len(values)
        if user_progress.recent_scores:
            return self.rolling_average(user_progress.recent_scores)
        return 0.0

    def _recommended_review_topics(self, user_progress: UserProgress, topic_id: str | None) -> tuple[str, ...]:
        if topic_id is not None:
            blocking_topics = self.content_library.blocking_topics_for_user(
                topic_id=topic_id,
                user_progress=user_progress,
                mastery_threshold=self.mastery_threshold,
                b2_prerequisite_threshold=self.b2_prerequisite_threshold,
            )
            if blocking_topics:
                return tuple(topic.topic_id for topic in blocking_topics)

            topic = self.content_library.get_topic(topic_id)
            if topic is not None and user_progress.mastery_matrix.get(topic.topic_id, 0.0) < self.mastery_threshold:
                return (topic.topic_id,)

        return tuple(
            topic.topic_id
            for topic in self.content_library.all_topics()
            if topic.level <= user_progress.current_level
            and user_progress.mastery_matrix.get(topic.topic_id, 0.0) < self.mastery_threshold
        )[:3]
