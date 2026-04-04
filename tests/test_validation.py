import pytest

from app.models import CEFRBand
from app.services import ContentLibrary
from app.validation import ContentValidationError, ContentValidator, lesson_to_payload


def test_content_validator_accepts_valid_fallback_lesson():
    content_library = ContentLibrary()
    validator = ContentValidator()
    lesson = content_library.build_fallback_lesson(
        "nouns_and_articles",
        difficulty=3,
        question_count=5,
    )
    topic = content_library.get_topic("nouns_and_articles")
    assert topic is not None

    validated = validator.validate_lesson_payload(
        lesson_to_payload(lesson),
        topic=topic,
        expected_question_count=5,
    )

    assert validated.topic == "nouns_and_articles"
    assert validated.cefr_band == CEFRBand.A1
    assert len(validated.quiz_questions) == 5


def test_content_validator_rejects_off_scope_and_duplicate_prompts():
    content_library = ContentLibrary()
    validator = ContentValidator()
    topic = content_library.get_topic("present_tense_verbs")
    assert topic is not None
    payload = {
        "lesson_id": "lesson-1",
        "topic": "present_tense_verbs",
        "level": 4,
        "cefr_band": "A1",
        "difficulty": 3,
        "explanation_text": "This lesson is about verbs but the content drifts away from the target.",
        "example_sentences": [
            {"romanian": "Eu merg acasa.", "english": "I go home."},
        ],
        "key_rules": ["Use present tense endings with the correct subject."],
        "quiz_questions": [
            {
                "question_id": "q1",
                "type": "multiple_choice",
                "prompt": "Choose the correct present tense form.",
                "options": ["merg", "merge", "mergem"],
                "correct_answer": "merge",
                "explanation": "Because it fits.",
                "difficulty": 3,
                "tags": ["nouns_and_articles"],
                "hint": "Pick one.",
                "rubric": {},
                "cefr_band": "A1",
            },
            {
                "question_id": "q2",
                "type": "multiple_choice",
                "prompt": "Choose the correct present tense form.",
                "options": ["scriu", "scrie"],
                "correct_answer": "scrie",
                "explanation": "This still duplicates the prompt and stays off scope.",
                "difficulty": 3,
                "tags": ["nouns_and_articles"],
                "hint": "Pick one.",
                "rubric": {},
                "cefr_band": "A1",
            },
        ],
    }

    with pytest.raises(ContentValidationError) as exc_info:
        validator.validate_lesson_payload(
            payload,
            topic=topic,
            expected_question_count=2,
        )

    messages = [issue.message for issue in exc_info.value.issues]
    assert any("Question tags do not match the requested lesson scope" in message for message in messages)
    assert any("Duplicate question prompt" in message for message in messages)


def test_content_validator_rejects_duplicate_options():
    content_library = ContentLibrary()
    validator = ContentValidator()
    topic = content_library.get_topic("present_tense_verbs")
    assert topic is not None
    payload = {
        "lesson_id": "lesson-2",
        "topic": "present_tense_verbs",
        "level": 4,
        "cefr_band": "A1",
        "difficulty": 3,
        "explanation_text": "This lesson stays on topic but includes a malformed multiple choice item.",
        "example_sentences": [
            {"romanian": "Noi scriem acum.", "english": "We write now."},
        ],
        "key_rules": ["Present tense endings must match the subject."],
        "quiz_questions": [
            {
                "question_id": "q1",
                "type": "multiple_choice",
                "prompt": "Pick the correct present tense ending for 'noi'.",
                "options": ["scriem", "scriem", "scriu"],
                "correct_answer": "scriem",
                "explanation": "The correct form is first-person plural.",
                "difficulty": 3,
                "tags": ["present_tense_verbs"],
                "hint": "Pick one.",
                "rubric": {},
                "cefr_band": "A1",
            },
        ],
    }

    with pytest.raises(ContentValidationError) as exc_info:
        validator.validate_lesson_payload(
            payload,
            topic=topic,
            expected_question_count=1,
        )

    messages = [issue.message for issue in exc_info.value.issues]
    assert any("Options must be unique" in message for message in messages)


def test_content_validator_accepts_b1_transformation_and_dialogue_tasks():
    content_library = ContentLibrary()
    validator = ContentValidator()
    topic = content_library.get_topic("narrative_b1_grammar")
    assert topic is not None
    payload = {
        "lesson_id": "lesson-b1-1",
        "topic": "narrative_b1_grammar",
        "level": 7,
        "cefr_band": "B1",
        "difficulty": 7,
        "explanation_text": "This lesson contrasts ongoing background actions with completed past events in short everyday narratives.",
        "example_sentences": [
            {
                "romanian": "Cind mergeam spre gara, a inceput sa ploua. Am alergat repede spre autobuz.",
                "english": "While I was walking to the station, it started to rain. I ran quickly to the bus.",
            }
        ],
        "key_rules": [
            "Use the imperfect for background context.",
            "Use the perfect compound for completed events.",
        ],
        "quiz_questions": [
            {
                "question_id": "q1",
                "type": "sentence_transformation",
                "prompt": "Sentence transformation: Rewrite 'I was eating when he called' with an imperfect background and a completed event.",
                "options": [],
                "correct_answer": "Mincam cind a sunat el.",
                "explanation": "The background action uses the imperfect and the interrupting call uses a completed past form.",
                "difficulty": 7,
                "tags": ["narrative_b1_grammar", "imperfect"],
                "hint": "Use one ongoing past action and one finished event.",
                "rubric": {},
                "cefr_band": "B1",
            },
            {
                "question_id": "q2",
                "type": "dialogue_completion",
                "prompt": "Dialogue completion: Complete the reply in a realistic way. 'De ce lipsesti miine?' 'Nu pot veni pentru ca ___ sa lucrez pina seara.'",
                "options": [],
                "correct_answer": "trebuie",
                "explanation": "The reply needs an obligation structure that fits the reason for missing the event.",
                "difficulty": 7,
                "tags": ["narrative_b1_grammar", "obligation"],
                "hint": "Use the common word for obligation.",
                "rubric": {},
                "cefr_band": "B1",
            },
        ],
    }

    validated = validator.validate_lesson_payload(payload, topic=topic, expected_question_count=2)

    assert validated.cefr_band == CEFRBand.B1
    assert validated.quiz_questions[0].question_type.value == "sentence_transformation"
    assert validated.quiz_questions[1].question_type.value == "dialogue_completion"


def test_content_validator_accepts_b2_reading_and_guided_writing_tasks():
    content_library = ContentLibrary()
    validator = ContentValidator()
    topic = content_library.get_topic("b2_core_structures")
    assert topic is not None
    payload = {
        "lesson_id": "lesson-b2-1",
        "topic": "b2_core_structures",
        "level": 9,
        "cefr_band": "B2",
        "difficulty": 9,
        "explanation_text": "This lesson combines reported speech, connector control, and paragraph-level comprehension.",
        "example_sentences": [
            {
                "romanian": "Directorul a spus ca proiectul va continua, desi costurile au crescut. Raportul final va fi trimis clientilor saptamina viitoare.",
                "english": "The director said the project would continue, although costs increased. The final report will be sent to clients next week.",
            },
            {
                "romanian": "In oras se discuta despre transportul public, deoarece traficul s-a agravat. Totusi, unele solutii vor functiona numai daca sint aplicate consecvent.",
                "english": "In the city, public transport is being discussed because traffic has worsened. However, some solutions will work only if they are applied consistently.",
            },
        ],
        "key_rules": [
            "Use connectors to organise extended meaning.",
            "Keep reported and passive structures natural inside a coherent context.",
        ],
        "quiz_questions": [
            {
                "question_id": "q1",
                "type": "reading_comprehension",
                "prompt": "Reading comprehension: Read the passage and answer in English. 'Directorul a spus ca proiectul va continua, desi costurile au crescut. Raportul final va fi trimis clientilor saptamina viitoare.' What will be sent next week?",
                "options": [],
                "correct_answer": "The final report will be sent to clients next week.",
                "explanation": "The second sentence states that the final report will be sent to clients the following week.",
                "difficulty": 9,
                "tags": ["b2_core_structures", "reported_speech"],
                "hint": "Check the second sentence.",
                "rubric": {},
                "cefr_band": "B2",
            },
            {
                "question_id": "q2",
                "type": "guided_writing",
                "prompt": "Guided writing: Write two or three Romanian sentences giving your opinion about public transport. Use at least one connector of contrast or conclusion.",
                "options": [],
                "correct_answer": "Transportul public trebuie imbunatatit, deoarece traficul este dificil. Totusi, investitiile trebuie planificate atent. Prin urmare, orasul are nevoie de solutii clare.",
                "explanation": "A valid answer gives an opinion, supports it, and links ideas with connectors.",
                "difficulty": 9,
                "tags": ["b2_core_structures", "advanced_connectors"],
                "hint": "State an opinion, support it, and conclude.",
                "rubric": {
                    "task_completion": "Gives and supports an opinion.",
                    "connector_control": "Uses a connector appropriately.",
                },
                "cefr_band": "B2",
            },
        ],
    }

    validated = validator.validate_lesson_payload(payload, topic=topic, expected_question_count=2)

    assert validated.cefr_band == CEFRBand.B2
    assert any(question.question_type.value == "reading_comprehension" for question in validated.quiz_questions)
    assert any(question.question_type.value == "guided_writing" for question in validated.quiz_questions)


def test_content_validator_rejects_dialogue_prompt_without_dialogue_context():
    content_library = ContentLibrary()
    validator = ContentValidator()
    topic = content_library.get_topic("romanian_basics")
    assert topic is not None
    payload = {
        "lesson_id": "lesson-a1-dialogue-bad",
        "topic": "romanian_basics",
        "level": 1,
        "cefr_band": "A1",
        "difficulty": 2,
        "explanation_text": "This lesson tries to teach a fi but one prompt is not actually assessable.",
        "example_sentences": [
            {"romanian": "Eu sunt aici.", "english": "I am here."},
        ],
        "key_rules": ["Use forms of a fi with the right subject."],
        "quiz_questions": [
            {
                "question_id": "q1",
                "type": "fill_in_the_blank",
                "prompt": "Complete the dialogue with the appropriate forms of a fi.",
                "options": [],
                "correct_answer": "sunt",
                "explanation": "The answer should be the correct form of a fi.",
                "difficulty": 2,
                "tags": ["romanian_basics", "a_fi_present"],
                "hint": "Use the present tense.",
                "rubric": {},
                "cefr_band": "A1",
            },
        ],
    }

    with pytest.raises(ContentValidationError) as exc_info:
        validator.validate_lesson_payload(payload, topic=topic, expected_question_count=1)

    assert any(
        "does not include the actual dialogue context" in issue.message
        for issue in exc_info.value.issues
    )
