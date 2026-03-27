from __future__ import annotations

from collections.abc import Mapping

from app.models import PLACEMENT_TEST_BLUEPRINT, CEFRBand, PlacementTestSection, ROADMAP_TOPICS, TopicMetadata, UserProgress


class ContentLibrary:
    def __init__(
        self,
        topics: tuple[TopicMetadata, ...] = ROADMAP_TOPICS,
        placement_blueprint: tuple[PlacementTestSection, ...] = PLACEMENT_TEST_BLUEPRINT,
    ) -> None:
        self._topics = tuple(sorted(topics, key=lambda topic: topic.level))
        self._topics_by_id = {topic.topic_id: topic for topic in topics}
        self._placement_blueprint = placement_blueprint
        self._validate_topics()
        self._validate_placement_blueprint()

    def all_topics(self) -> tuple[TopicMetadata, ...]:
        return self._topics

    def get_topic(self, topic_id: str) -> TopicMetadata | None:
        return self._topics_by_id.get(topic_id)

    def topics_for_band(self, cefr_band: CEFRBand) -> tuple[TopicMetadata, ...]:
        return tuple(topic for topic in self._topics if topic.cefr_band == cefr_band)

    def placement_blueprint(self) -> tuple[PlacementTestSection, ...]:
        return self._placement_blueprint

    def target_cefr_band(self, level: int) -> CEFRBand:
        if level < 1:
            raise ValueError("Level must be at least 1.")
        candidate = self._topics[-1]
        for topic in self._topics:
            if level <= topic.level:
                candidate = topic
                break
        return candidate.cefr_band

    def available_topics(
        self,
        mastery_matrix: Mapping[str, float],
        mastery_threshold: float = 0.75,
    ) -> tuple[TopicMetadata, ...]:
        self._validate_mastery_threshold(mastery_threshold)
        return tuple(
            topic
            for topic in self._topics
            if all(mastery_matrix.get(prerequisite, 0.0) >= mastery_threshold for prerequisite in topic.prerequisites)
        )

    def next_topic_for_user(
        self,
        user_progress: UserProgress,
        mastery_threshold: float = 0.75,
    ) -> TopicMetadata | None:
        self._validate_mastery_threshold(mastery_threshold)
        mastery_matrix = user_progress.mastery_matrix
        for topic in self._topics:
            score = mastery_matrix.get(topic.topic_id, 0.0)
            if score >= mastery_threshold:
                continue
            blocking_topic = self._first_unmastered_prerequisite(topic, mastery_matrix, mastery_threshold)
            if blocking_topic is not None:
                return blocking_topic
            return topic
        return None

    def blocking_topics_for_user(
        self,
        topic_id: str,
        user_progress: UserProgress,
        mastery_threshold: float = 0.75,
        b2_prerequisite_threshold: float = 0.8,
    ) -> tuple[TopicMetadata, ...]:
        self._validate_mastery_threshold(mastery_threshold)
        self._validate_mastery_threshold(b2_prerequisite_threshold)
        topic = self._require_topic(topic_id)
        mastery_matrix = user_progress.mastery_matrix
        blocking_topics: list[TopicMetadata] = []
        seen: set[str] = set()

        def visit(candidate: TopicMetadata, threshold: float) -> None:
            for prerequisite_id in candidate.prerequisites:
                prerequisite = self._topics_by_id[prerequisite_id]
                visit(prerequisite, threshold)
                if mastery_matrix.get(prerequisite_id, 0.0) < threshold and prerequisite_id not in seen:
                    blocking_topics.append(prerequisite)
                    seen.add(prerequisite_id)

        visit(topic, mastery_threshold)
        if topic.cefr_band == CEFRBand.B2:
            for b1_topic in self.topics_for_band(CEFRBand.B1):
                if mastery_matrix.get(b1_topic.topic_id, 0.0) < b2_prerequisite_threshold and b1_topic.topic_id not in seen:
                    blocking_topics.append(b1_topic)
                    seen.add(b1_topic.topic_id)
        return tuple(blocking_topics)

    def is_topic_unlocked(
        self,
        topic_id: str,
        user_progress: UserProgress,
        mastery_threshold: float = 0.75,
        b2_prerequisite_threshold: float = 0.8,
    ) -> bool:
        return not self.blocking_topics_for_user(
            topic_id=topic_id,
            user_progress=user_progress,
            mastery_threshold=mastery_threshold,
            b2_prerequisite_threshold=b2_prerequisite_threshold,
        )

    def _first_unmastered_prerequisite(
        self,
        topic: TopicMetadata,
        mastery_matrix: Mapping[str, float],
        mastery_threshold: float,
    ) -> TopicMetadata | None:
        for prerequisite_id in topic.prerequisites:
            prerequisite = self._topics_by_id[prerequisite_id]
            blocking_topic = self._first_unmastered_prerequisite(prerequisite, mastery_matrix, mastery_threshold)
            if blocking_topic is not None:
                return blocking_topic
            if mastery_matrix.get(prerequisite_id, 0.0) < mastery_threshold:
                return prerequisite
        return None

    def _validate_mastery_threshold(self, mastery_threshold: float) -> None:
        if not 0.0 <= mastery_threshold <= 1.0:
            raise ValueError("Mastery threshold must be between 0.0 and 1.0.")

    def _require_topic(self, topic_id: str) -> TopicMetadata:
        topic = self.get_topic(topic_id)
        if topic is None:
            raise ValueError(f"Unknown topic '{topic_id}'.")
        return topic

    def _validate_topics(self) -> None:
        if len(self._topics_by_id) != len(self._topics):
            raise ValueError("Topic ids must be unique.")
        expected_levels = list(range(1, len(self._topics) + 1))
        actual_levels = [topic.level for topic in self._topics]
        if actual_levels != expected_levels:
            raise ValueError("Roadmap levels must be contiguous and start at 1.")
        for topic in self._topics:
            for prerequisite_id in topic.prerequisites:
                if prerequisite_id not in self._topics_by_id:
                    raise ValueError(f"Unknown prerequisite '{prerequisite_id}' for topic '{topic.topic_id}'.")
                if self._topics_by_id[prerequisite_id].level >= topic.level:
                    raise ValueError("Prerequisites must point to earlier levels.")

    def _validate_placement_blueprint(self) -> None:
        if not self._placement_blueprint:
            raise ValueError("Placement blueprint cannot be empty.")
        topic_ids = {topic.topic_id for topic in self._topics}
        covered_bands = {section.cefr_band for section in self._placement_blueprint}
        if covered_bands != {CEFRBand.A1, CEFRBand.A2, CEFRBand.B1, CEFRBand.B2}:
            raise ValueError("Placement blueprint must cover A1, A2, B1, and B2.")
        for section in self._placement_blueprint:
            if section.question_count < 1:
                raise ValueError("Placement sections must include at least one question.")
            low, high = section.target_difficulty
            if low < 1 or high > 10 or low > high:
                raise ValueError("Placement section difficulty ranges must fit within 1 to 10.")
            for topic_id in section.topic_ids:
                if topic_id not in topic_ids:
                    raise ValueError(f"Unknown placement topic '{topic_id}' in section '{section.section_id}'.")
