from __future__ import annotations

from dataclasses import dataclass

from app.models.domain import CEFRBand


@dataclass(frozen=True, slots=True)
class TopicMetadata:
    topic_id: str
    title: str
    description: str
    level: int
    cefr_band: CEFRBand
    prerequisites: tuple[str, ...] = ()
    grammar_focus: tuple[str, ...] = ()


ROADMAP_TOPICS: tuple[TopicMetadata, ...] = (
    TopicMetadata(
        topic_id="romanian_basics",
        title="Romanian Basics",
        description="Diacritics, pronunciation, greetings, and the verb 'a fi' in the present tense.",
        level=1,
        cefr_band=CEFRBand.A1,
        grammar_focus=("diacritics", "pronunciation", "greetings", "a_fi_present"),
    ),
    TopicMetadata(
        topic_id="nouns_and_articles",
        title="Nouns and Articles",
        description="Core noun genders and the contrast between indefinite and definite noun forms.",
        level=2,
        cefr_band=CEFRBand.A1,
        prerequisites=("romanian_basics",),
        grammar_focus=("noun_gender", "plural_patterns", "definite_articles"),
    ),
    TopicMetadata(
        topic_id="core_cases",
        title="Core Cases",
        description="Nominative, accusative, genitive, and dative in guided sentence patterns.",
        level=3,
        cefr_band=CEFRBand.A1,
        prerequisites=("nouns_and_articles",),
        grammar_focus=("nominative", "accusative", "genitive", "dative"),
    ),
    TopicMetadata(
        topic_id="present_tense_verbs",
        title="Present Tense Verbs",
        description="Present tense conjugation patterns and subject-verb agreement with common verbs.",
        level=4,
        cefr_band=CEFRBand.A1,
        prerequisites=("core_cases",),
        grammar_focus=("verb_groups", "present_tense", "agreement"),
    ),
    TopicMetadata(
        topic_id="pronouns_and_tenses",
        title="Pronouns and Core Tense Expansion",
        description="Pronouns, reflexive constructions, and the first contrastive tense work.",
        level=5,
        cefr_band=CEFRBand.A2,
        prerequisites=("present_tense_verbs",),
        grammar_focus=("subject_pronouns", "object_pronouns", "perfect_compound", "future"),
    ),
    TopicMetadata(
        topic_id="connected_communication",
        title="Connected Everyday Communication",
        description="Imperatives, adverbs, sequencing, and simple multi-clause daily communication.",
        level=6,
        cefr_band=CEFRBand.A2,
        prerequisites=("pronouns_and_tenses",),
        grammar_focus=("imperative", "adverbs", "comparisons", "sequencing"),
    ),
)
