from __future__ import annotations

from app.models import ROADMAP_TOPICS, CEFRBand, TopicMetadata


class ContentLibrary:
    def __init__(self, topics: tuple[TopicMetadata, ...] = ROADMAP_TOPICS) -> None:
        self._topics = topics
        self._topics_by_id = {topic.topic_id: topic for topic in topics}

    def all_topics(self) -> tuple[TopicMetadata, ...]:
        return self._topics

    def get_topic(self, topic_id: str) -> TopicMetadata | None:
        return self._topics_by_id.get(topic_id)

    def topics_for_band(self, cefr_band: CEFRBand) -> tuple[TopicMetadata, ...]:
        return tuple(topic for topic in self._topics if topic.cefr_band == cefr_band)
