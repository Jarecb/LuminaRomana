"""Roadmap metadata and placement test blueprints.

Holds TopicMetadata and PlacementTestSection dataclasses and the canonical roadmap
and placement-test blueprints used by the learning content library.
"""
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


@dataclass(frozen=True, slots=True)
class PlacementTestSection:
    section_id: str
    cefr_band: CEFRBand
    title: str
    description: str
    topic_ids: tuple[str, ...]
    question_count: int
    target_difficulty: tuple[int, int]


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
    TopicMetadata(
        topic_id="narrative_b1_grammar",
        title="Narrative and Functional B1 Grammar",
        description="Narrative tense contrast, motion and obligation structures, and practical relative clauses.",
        level=7,
        cefr_band=CEFRBand.B1,
        prerequisites=("connected_communication",),
        grammar_focus=("imperfect", "perfect_compound_contrast", "motion", "obligation", "relative_clauses"),
    ),
    TopicMetadata(
        topic_id="b1_b2_transition",
        title="B1 to B2 Transition",
        description="Conditional mood, more complex pronoun placement, and subordinate clauses for cause and contrast.",
        level=8,
        cefr_band=CEFRBand.B1,
        prerequisites=("narrative_b1_grammar",),
        grammar_focus=("conditional", "complex_pronouns", "subordinate_clauses", "register_awareness"),
    ),
    TopicMetadata(
        topic_id="b2_core_structures",
        title="B2 Core Structures",
        description="Passive and impersonal constructions, reported speech, and connector-driven paragraph development.",
        level=9,
        cefr_band=CEFRBand.B2,
        prerequisites=("b1_b2_transition",),
        grammar_focus=("passive_voice", "impersonal_forms", "reported_speech", "advanced_connectors"),
    ),
    TopicMetadata(
        topic_id="b2_consolidation",
        title="B2 Consolidation",
        description="Mixed tense review, nuanced case and article use, and integrated reading and writing tasks.",
        level=10,
        cefr_band=CEFRBand.B2,
        prerequisites=("b2_core_structures",),
        grammar_focus=("mixed_tenses", "nuanced_case_usage", "error_correction", "integrated_writing"),
    ),
)


PLACEMENT_TEST_BLUEPRINT: tuple[PlacementTestSection, ...] = (
    PlacementTestSection(
        section_id="placement_a1_foundations",
        cefr_band=CEFRBand.A1,
        title="A1 Foundations",
        description="Checks diacritics, greetings, core noun/article use, and the first present-tense patterns.",
        topic_ids=("romanian_basics", "nouns_and_articles", "core_cases", "present_tense_verbs"),
        question_count=12,
        target_difficulty=(1, 3),
    ),
    PlacementTestSection(
        section_id="placement_a2_everyday_use",
        cefr_band=CEFRBand.A2,
        title="A2 Everyday Use",
        description="Checks pronouns, tense expansion, sequencing, and daily-life communication tasks.",
        topic_ids=("pronouns_and_tenses", "connected_communication"),
        question_count=10,
        target_difficulty=(3, 5),
    ),
    PlacementTestSection(
        section_id="placement_b1_functional_range",
        cefr_band=CEFRBand.B1,
        title="B1 Functional Range",
        description="Checks narrative tense control, practical writing patterns, and subordinate-clause comprehension.",
        topic_ids=("narrative_b1_grammar", "b1_b2_transition"),
        question_count=10,
        target_difficulty=(6, 8),
    ),
    PlacementTestSection(
        section_id="placement_b2_integrated_control",
        cefr_band=CEFRBand.B2,
        title="B2 Integrated Control",
        description="Checks paragraph-level control, argument connectors, reported speech, and mixed-grammar editing.",
        topic_ids=("b2_core_structures", "b2_consolidation"),
        question_count=12,
        target_difficulty=(8, 10),
    ),
)
