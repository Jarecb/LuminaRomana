from app.models import CEFRBand
from app.services import ContentLibrary
import random


def test_content_library_exposes_seeded_topics():
    library = ContentLibrary()

    basics = library.get_topic("romanian_basics")
    a2_topics = library.topics_for_band(CEFRBand.A2)
    b2_topics = library.topics_for_band(CEFRBand.B2)

    assert basics is not None
    assert basics.level == 1
    assert basics.cefr_band == CEFRBand.A1
    assert len(a2_topics) == 2
    assert a2_topics[0].topic_id == "pronouns_and_tenses"
    assert len(b2_topics) == 2


def test_content_library_maps_levels_to_cefr_bands():
    library = ContentLibrary()

    assert library.target_cefr_band(1) == CEFRBand.A1
    assert library.target_cefr_band(4) == CEFRBand.A1
    assert library.target_cefr_band(5) == CEFRBand.A2
    assert library.target_cefr_band(7) == CEFRBand.B1
    assert library.target_cefr_band(10) == CEFRBand.B2


def test_next_topic_for_new_user_returns_first_topic():
    from app.models import UserProgress

    library = ContentLibrary()
    user_progress = UserProgress(user_id="user-1")

    next_topic = library.next_topic_for_user(user_progress)

    assert next_topic is not None
    assert next_topic.topic_id == "romanian_basics"


def test_next_topic_advances_when_prior_topic_is_mastered():
    from app.models import UserProgress

    library = ContentLibrary()
    user_progress = UserProgress(
        user_id="user-1",
        mastery_matrix={
            "romanian_basics": 0.90,
            "nouns_and_articles": 0.82,
            "core_cases": 0.79,
        },
    )

    next_topic = library.next_topic_for_user(user_progress)

    assert next_topic is not None
    assert next_topic.topic_id == "present_tense_verbs"


def test_next_topic_returns_blocking_prerequisite_before_later_topic():
    from app.models import UserProgress

    library = ContentLibrary()
    user_progress = UserProgress(
        user_id="user-1",
        current_level=8,
        current_cefr_band=CEFRBand.B1,
        mastery_matrix={
            "romanian_basics": 0.90,
            "nouns_and_articles": 0.80,
            "core_cases": 0.82,
            "present_tense_verbs": 0.85,
            "pronouns_and_tenses": 0.78,
            "connected_communication": 0.40,
            "narrative_b1_grammar": 0.0,
        },
    )

    next_topic = library.next_topic_for_user(user_progress)

    assert next_topic is not None
    assert next_topic.topic_id == "connected_communication"


def test_available_topics_require_mastered_prerequisites():
    library = ContentLibrary()

    available_topics = library.available_topics(
        mastery_matrix={
            "romanian_basics": 0.80,
            "nouns_and_articles": 0.76,
        }
    )

    assert [topic.topic_id for topic in available_topics] == [
        "romanian_basics",
        "nouns_and_articles",
        "core_cases",
    ]


def test_b2_topics_remain_locked_when_b1_mastery_is_below_threshold():
    from app.models import UserProgress

    library = ContentLibrary()
    user_progress = UserProgress(
        user_id="user-1",
        current_level=9,
        current_cefr_band=CEFRBand.B1,
        mastery_matrix={
            "romanian_basics": 0.90,
            "nouns_and_articles": 0.88,
            "core_cases": 0.86,
            "present_tense_verbs": 0.91,
            "pronouns_and_tenses": 0.82,
            "connected_communication": 0.80,
            "narrative_b1_grammar": 0.79,
            "b1_b2_transition": 0.77,
        },
    )

    blocking_topics = library.blocking_topics_for_user("b2_core_structures", user_progress)

    assert library.is_topic_unlocked("b2_core_structures", user_progress) is False
    assert [topic.topic_id for topic in blocking_topics] == [
        "narrative_b1_grammar",
        "b1_b2_transition",
    ]


def test_placement_blueprint_spans_a1_to_b2():
    library = ContentLibrary()

    sections = library.placement_blueprint()

    assert [section.cefr_band for section in sections] == [
        CEFRBand.A1,
        CEFRBand.A2,
        CEFRBand.B1,
        CEFRBand.B2,
    ]
    assert all(section.question_count >= 10 for section in sections)
    assert "b2_consolidation" in sections[-1].topic_ids


def test_fallback_question_pools_are_larger_than_one_question_set():
    library = ContentLibrary()

    lesson = library.build_fallback_lesson("romanian_basics", difficulty=2, question_count=5)

    assert len({question.prompt for question in lesson.quiz_questions}) == 5
    baseline_pool = {question.prompt for question in library.build_fallback_lesson("romanian_basics", difficulty=2, question_count=8).quiz_questions}
    assert len(baseline_pool) >= 8


def test_fallback_lessons_can_draw_different_question_sets():
    library = ContentLibrary()
    random.seed(1)
    first = library.build_fallback_lesson("nouns_and_articles", difficulty=3, question_count=5)
    random.seed(2)
    second = library.build_fallback_lesson("nouns_and_articles", difficulty=3, question_count=5)

    assert [question.prompt for question in first.quiz_questions] != [question.prompt for question in second.quiz_questions]


def test_b1_fallback_support_includes_integrated_tasks_and_vocab():
    library = ContentLibrary()

    lesson = library.build_fallback_lesson("narrative_b1_grammar", difficulty=7, question_count=5)
    vocab = library.vocabulary_for_topic("narrative_b1_grammar")

    assert lesson.cefr_band == CEFRBand.B1
    assert len(lesson.example_sentences) >= 2
    assert any(question.question_type.value == "sentence_transformation" for question in lesson.quiz_questions)
    assert any(question.question_type.value == "dialogue_completion" for question in lesson.quiz_questions)
    assert ("trebuie", "must / have to") in vocab
