from app.models import CEFRBand
from app.services import ContentLibrary


def test_content_library_exposes_seeded_topics():
    library = ContentLibrary()

    basics = library.get_topic("romanian_basics")
    a2_topics = library.topics_for_band(CEFRBand.A2)

    assert basics is not None
    assert basics.level == 1
    assert basics.cefr_band == CEFRBand.A1
    assert len(a2_topics) == 2
    assert a2_topics[0].topic_id == "pronouns_and_tenses"
