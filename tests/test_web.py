from __future__ import annotations

from io import BytesIO
from urllib.parse import urlencode
from wsgiref.util import setup_testing_defaults

from app.bootstrap import create_application
from app.models import CEFRBand, Question, QuestionType
from app.ui import create_web_app


def request(app, method: str, path: str, data: dict[str, str] | None = None):
    environ = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = method
    if "?" in path:
        path_info, query_string = path.split("?", 1)
    else:
        path_info, query_string = path, ""
    environ["PATH_INFO"] = path_info
    environ["QUERY_STRING"] = query_string
    body = b""
    if data is not None:
        body = urlencode(data).encode("utf-8")
        environ["CONTENT_LENGTH"] = str(len(body))
        environ["CONTENT_TYPE"] = "application/x-www-form-urlencoded"
    else:
        environ["CONTENT_LENGTH"] = "0"
    environ["wsgi.input"] = BytesIO(body)

    captured: dict[str, object] = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    chunks = app(environ, start_response)
    body_bytes = b"".join(chunks)
    return captured["status"], dict(captured["headers"]), body_bytes.decode("utf-8")


def build_offline_question(topic_id: str, index: int) -> Question:
    return Question(
        question_id=f"offline-{topic_id}-{index}",
        prompt=f"Unique prompt {index}: choose the correct form for {topic_id}.",
        question_type=QuestionType.MULTIPLE_CHOICE,
        difficulty_rating=2,
        cefr_band=CEFRBand.A1,
        correct_answer=f"answer-{index}",
        explanation=f"Explanation for question {index}.",
        tags=[topic_id],
        options=[f"answer-{index}", f"distractor-{index}-a", f"distractor-{index}-b"],
        hint="Pick the exact matching answer.",
    )


def test_dashboard_and_progress_pages_render(monkeypatch, tmp_path):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(tmp_path / "data"))
    web_app = create_web_app(create_application())

    status, _, dashboard_html = request(web_app, "GET", "/")
    progress_status, _, progress_html = request(web_app, "GET", "/progress")
    wordbank_status, _, wordbank_html = request(web_app, "GET", "/wordbank")

    assert status == "200 OK"
    assert "Lesson loop ready" in dashboard_html
    assert "Start or resume session" in dashboard_html
    assert "Wordbank" in dashboard_html
    assert progress_status == "200 OK"
    assert "Learner progress" in progress_html
    assert wordbank_status == "200 OK"
    assert "Saved vocabulary" in wordbank_html


def test_lesson_and_quiz_flow_render_explanations(monkeypatch, tmp_path):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(tmp_path / "data"))
    web_app = create_web_app(create_application())

    start_status, start_headers, _ = request(web_app, "POST", "/sessions/start", {})
    lesson_path = start_headers["Location"]
    lesson_status, _, lesson_html = request(web_app, "GET", lesson_path)

    assert start_status == "302 Found"
    assert lesson_path.startswith("/lessons/")
    assert lesson_status == "200 OK"
    assert "Question set" in lesson_html
    assert "Revision page" in lesson_html
    assert "Submit answers" in lesson_html

    lesson_id = lesson_path.removeprefix("/lessons/")
    lesson = web_app.learning_service.lesson_repository.get(lesson_id)
    assert lesson is not None

    submit_data = {
        f"answer_{question.question_id}": question.correct_answer
        for question in lesson.quiz_questions
    }
    result_status, _, result_html = request(web_app, "POST", f"{lesson_path}/submit", submit_data)
    progress_status, _, progress_html = request(web_app, "GET", "/progress")

    assert result_status == "200 OK"
    assert "Answer explanations" in result_html
    assert "100%" in result_html
    assert "Running level average" in result_html
    assert "five completed question sets" in result_html
    assert "&#10003;" in result_html
    assert "Correct" in result_html
    assert progress_status == "200 OK"
    assert "Current level 1" in progress_html


def test_wrong_answer_result_page_shows_why_it_is_wrong(monkeypatch, tmp_path):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(tmp_path / "data"))
    web_app = create_web_app(create_application())

    _, start_headers, _ = request(web_app, "POST", "/sessions/start", {})
    lesson_path = start_headers["Location"]
    lesson_id = lesson_path.removeprefix("/lessons/")
    lesson = web_app.learning_service.lesson_repository.get(lesson_id)
    assert lesson is not None

    bad_submit_data = {f"answer_{question.question_id}": "" for question in lesson.quiz_questions}
    result_status, _, result_html = request(web_app, "POST", f"{lesson_path}/submit", bad_submit_data)

    assert result_status == "200 OK"
    assert "Why this was wrong" in result_html
    assert "&#10007;" in result_html


def test_result_page_shows_mastery_gate_message_for_pending_incorrect_answers(monkeypatch, tmp_path):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(tmp_path / "data"))
    web_app = create_web_app(create_application())
    web_app.application.persistence.offline_questions.upsert_questions(
        "romanian_basics",
        [build_offline_question("romanian_basics", index) for index in range(1, 31)],
    )

    last_lesson_path = ""
    last_lesson = None
    for attempt_index in range(5):
        _, start_headers, _ = request(web_app, "POST", "/sessions/start", {})
        last_lesson_path = start_headers["Location"]
        lesson_id = last_lesson_path.removeprefix("/lessons/")
        last_lesson = web_app.learning_service.lesson_repository.get(lesson_id)
        assert last_lesson is not None

        submit_data = {
            f"answer_{question.question_id}": question.correct_answer
            for question in last_lesson.quiz_questions
        }
        if attempt_index == 4:
            submit_data[f"answer_{last_lesson.quiz_questions[0].question_id}"] = ""
        result_status, _, result_html = request(web_app, "POST", f"{last_lesson_path}/submit", submit_data)

    assert last_lesson is not None
    assert result_status == "200 OK"
    assert "previously incorrect question" in result_html
    assert "Retry missed questions" in result_html


def test_wordbank_search_finds_encountered_words(monkeypatch, tmp_path):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(tmp_path / "data"))
    web_app = create_web_app(create_application())

    _, start_headers, _ = request(web_app, "POST", "/sessions/start", {})
    lesson_path = start_headers["Location"]
    lesson_status, _, lesson_html = request(web_app, "GET", lesson_path)
    search_status, _, search_html = request(web_app, "GET", "/wordbank?q=hello")

    assert lesson_status == "200 OK"
    assert "Question set" in lesson_html
    assert search_status == "200 OK"
    assert "buna" in search_html
    assert "hello" in search_html


def test_b2_lesson_page_renders_reading_and_writing_workflow(monkeypatch, tmp_path):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(tmp_path / "data"))
    web_app = create_web_app(create_application())

    progress = web_app.learning_service.get_or_create_user_progress()
    progress.current_level = 9
    progress.current_cefr_band = web_app.learning_service.content_library.target_cefr_band(9)
    progress.current_difficulty = 9
    progress.mastery_matrix.update(
        {
            "romanian_basics": 0.9,
            "nouns_and_articles": 0.88,
            "core_cases": 0.86,
            "present_tense_verbs": 0.84,
            "pronouns_and_tenses": 0.82,
            "connected_communication": 0.8,
            "narrative_b1_grammar": 0.8,
            "b1_b2_transition": 0.8,
        }
    )
    web_app.learning_service.user_progress_repository.save(progress)

    session = web_app.learning_service.start_topic_lesson("b2_core_structures")
    assert session.lesson is not None

    lesson_status, _, lesson_html = request(web_app, "GET", f"/lessons/{session.lesson.lesson_id}")
    progress_status, _, progress_html = request(web_app, "GET", "/progress")

    assert lesson_status == "200 OK"
    assert "Reading comprehension" in lesson_html
    assert "Guided writing" in lesson_html
    assert "<textarea" in lesson_html
    assert "Scoring focus" in lesson_html
    assert "<blockquote>" in lesson_html
    assert progress_status == "200 OK"
    assert "Skill signals" in progress_html


def test_progress_page_can_revisit_completed_level_without_losing_position(monkeypatch, tmp_path):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(tmp_path / "data"))
    web_app = create_web_app(create_application())

    progress = web_app.learning_service.get_or_create_user_progress()
    progress.current_level = 5
    progress.current_cefr_band = web_app.learning_service.content_library.target_cefr_band(5)
    progress.current_difficulty = 5
    progress.mastery_matrix.update(
        {
            "romanian_basics": 0.9,
            "nouns_and_articles": 0.88,
            "core_cases": 0.86,
            "present_tense_verbs": 0.84,
        }
    )
    web_app.learning_service.user_progress_repository.save(progress)

    progress_status, _, progress_html = request(web_app, "GET", "/progress")
    revisit_status, revisit_headers, _ = request(
        web_app,
        "POST",
        "/progress/revisit",
        {"topic_id": "romanian_basics"},
    )
    lesson_path = revisit_headers["Location"]
    lesson_id = lesson_path.removeprefix("/lessons/")
    lesson = web_app.learning_service.lesson_repository.get(lesson_id)
    assert lesson is not None

    result_status, _, result_html = request(
        web_app,
        "POST",
        f"{lesson_path}/submit",
        {f"answer_{question.question_id}": "" for question in lesson.quiz_questions},
    )
    updated = web_app.learning_service.get_or_create_user_progress()

    assert progress_status == "200 OK"
    assert "Redo level" in progress_html
    assert revisit_status == "302 Found"
    assert "practice" in lesson.lesson_id
    assert result_status == "200 OK"
    assert "stored mastery and current roadmap position were not changed" in result_html
    assert updated.current_level == 5
    assert updated.current_cefr_band.value == "A2"


def test_offline_only_server_mode_uses_fallback_and_renders_banner(monkeypatch, tmp_path):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LUMINA_ROMANA_AI_ENABLED", "true")
    monkeypatch.setenv("LUMINA_ROMANA_AI_PROVIDER", "openai")
    monkeypatch.setenv("LUMINA_ROMANA_AI_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("LUMINA_ROMANA_AI_API_KEY", "test-key")

    def fail_if_called(self, messages, temperature):
        raise AssertionError("AI provider should not be called in offline-only mode.")

    monkeypatch.setattr("app.ai.providers.AIChatProvider.generate_json", fail_if_called)

    web_app = create_web_app(create_application(offline_only=True))

    status, _, dashboard_html = request(web_app, "GET", "/")
    start_status, start_headers, _ = request(web_app, "POST", "/sessions/start", {})
    lesson_path = start_headers["Location"]
    lesson_id = lesson_path.removeprefix("/lessons/")
    lesson = web_app.learning_service.lesson_repository.get(lesson_id)

    assert status == "200 OK"
    assert "Offline-only mode active." in dashboard_html
    assert start_status == "302 Found"
    assert lesson is not None
    assert lesson.lesson_id.startswith("fallback-")
