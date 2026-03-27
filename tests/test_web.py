from __future__ import annotations

from io import BytesIO
from urllib.parse import urlencode
from wsgiref.util import setup_testing_defaults

from app.bootstrap import create_application
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
    intro_path = start_headers["Location"]
    intro_status, _, intro_html = request(web_app, "GET", intro_path)
    begin_status, begin_headers, _ = request(web_app, "POST", f"{intro_path}/begin", {})
    revision_path = begin_headers["Location"]
    revision_status, _, revision_html = request(web_app, "GET", revision_path)
    practice_status, practice_headers, _ = request(web_app, "POST", f"{revision_path.removesuffix('/revision')}/practice", {})
    lesson_path = practice_headers["Location"]
    lesson_status, _, lesson_html = request(web_app, "GET", lesson_path)

    assert start_status == "302 Found"
    assert intro_status == "200 OK"
    assert "What this level teaches" in intro_html
    assert "diacritics" in intro_html or "a fi" in intro_html
    assert begin_status == "302 Found"
    assert revision_status == "200 OK"
    assert "Revision vocabulary" in revision_html
    assert "buna" in revision_html
    assert practice_status == "302 Found"
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
    intro_path = start_headers["Location"]
    _, begin_headers, _ = request(web_app, "POST", f"{intro_path}/begin", {})
    revision_path = begin_headers["Location"]
    _, practice_headers, _ = request(web_app, "POST", f"{revision_path.removesuffix('/revision')}/practice", {})
    lesson_path = practice_headers["Location"]
    lesson_id = lesson_path.removeprefix("/lessons/")
    lesson = web_app.learning_service.lesson_repository.get(lesson_id)
    assert lesson is not None

    bad_submit_data = {f"answer_{question.question_id}": "" for question in lesson.quiz_questions}
    result_status, _, result_html = request(web_app, "POST", f"{lesson_path}/submit", bad_submit_data)

    assert result_status == "200 OK"
    assert "Why this was wrong" in result_html
    assert "&#10007;" in result_html


def test_wordbank_search_finds_encountered_words(monkeypatch, tmp_path):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(tmp_path / "data"))
    web_app = create_web_app(create_application())

    _, start_headers, _ = request(web_app, "POST", "/sessions/start", {})
    intro_path = start_headers["Location"]
    _, begin_headers, _ = request(web_app, "POST", f"{intro_path}/begin", {})
    revision_path = begin_headers["Location"]
    revision_status, _, revision_html = request(web_app, "GET", revision_path)
    search_status, _, search_html = request(web_app, "GET", "/wordbank?q=hello")

    assert revision_status == "200 OK"
    assert "buna" in revision_html
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
