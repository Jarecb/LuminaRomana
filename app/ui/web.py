from __future__ import annotations

import traceback
from dataclasses import dataclass
from html import escape
from io import BytesIO
from typing import Callable
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from app.bootstrap import Application
from app.models import Question, QuestionType
from app.services.learning import (
    DEFAULT_USER_ID,
    DashboardData,
    LearningService,
    LessonSession,
    QuizResult,
)

HTMLResponse = tuple[str, list[tuple[str, str]], bytes]
ROMANIAN_CHARACTERS = ("ă", "â", "î", "ș", "ț", "Ă", "Â", "Î", "Ș", "Ț")


@dataclass(slots=True)
class WebApp:
    application: Application
    learning_service: LearningService

    def __call__(self, environ: dict, start_response: Callable) -> list[bytes]:
        try:
            method = environ.get("REQUEST_METHOD", "GET").upper()
            path = environ.get("PATH_INFO", "/") or "/"

            if method == "GET" and path == "/":
                response = self._html_response(self._render_dashboard())
            elif method == "POST" and path == "/sessions/start":
                session = self.learning_service.start_or_resume_lesson_session(DEFAULT_USER_ID)
                response = self._redirect(self._session_location(session))
            elif method == "GET" and path.startswith("/levels/"):
                level_path = path.removeprefix("/levels/")
                if level_path.endswith("/revision"):
                    topic_id = level_path.removesuffix("/revision")
                    response = self._html_response(self._render_level_revision(topic_id))
                else:
                    topic_id = level_path
                    response = self._html_response(self._render_level_intro(topic_id))
            elif method == "POST" and path.startswith("/levels/") and path.endswith("/begin"):
                topic_id = path.removeprefix("/levels/").removesuffix("/begin")
                # Using the original double-call logic from your source
                session = LessonSession(
                    page_kind="revision",
                    topic=self.learning_service.build_level_revision(DEFAULT_USER_ID, topic_id).topic,
                    session_goal=self.learning_service.build_level_revision(DEFAULT_USER_ID, topic_id).session_goal,
                    resumed=False,
                    source="system",
                    level_revision=self.learning_service.build_level_revision(DEFAULT_USER_ID, topic_id),
                )
                response = self._redirect(self._session_location(session))
            elif method == "POST" and path.startswith("/levels/") and path.endswith("/practice"):
                topic_id = path.removeprefix("/levels/").removesuffix("/practice")
                session = self.learning_service.start_topic_lesson(topic_id, user_id=DEFAULT_USER_ID)
                response = self._redirect(self._session_location(session))
            elif method == "GET" and path == "/wordbank":
                query = parse_qs(environ.get("QUERY_STRING", "")).get("q", [""])[-1]
                response = self._html_response(self._render_wordbank(query))
            elif method == "GET" and path == "/progress":
                response = self._html_response(self._render_progress())
            elif method == "POST" and path == "/progress/revisit":
                form_data = self._parse_form_data(environ)
                topic_id = form_data.get("topic_id", [""])[-1]
                session = self.learning_service.start_topic_lesson(
                    topic_id,
                    user_id=DEFAULT_USER_ID,
                    session_goal_override="practice",
                )
                response = self._redirect(self._session_location(session))
            elif method == "GET" and path.startswith("/lessons/"):
                lesson_id = path.removeprefix("/lessons/")
                response = self._html_response(self._render_lesson(lesson_id))
            elif method == "POST" and path.startswith("/lessons/") and path.endswith("/submit"):
                lesson_id = path.removeprefix("/lessons/").removesuffix("/submit")
                form_data = self._parse_form_data(environ)
                answers = {
                    key.removeprefix("answer_"): values[-1]
                    for key, values in form_data.items()
                    if key.startswith("answer_")
                }
                result = self.learning_service.submit_quiz(lesson_id, answers, user_id=DEFAULT_USER_ID)
                response = self._html_response(self._render_result(result))
            else:
                response = self._html_response(self._render_not_found(), status="404 Not Found")

            status, headers, body = response
            start_response(status, headers)
            return [body]

        except Exception as e:
            # This will force the error to appear in your terminal
            print("\n" + "=" * 80)
            print("SERVER ERROR DETECTED")
            print("=" * 80)
            traceback.print_exc()
            print("=" * 80 + "\n")

            # Simple fallback response so the browser doesn't just hang/reset
            start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
            return [f"Internal Server Error:\n{str(e)}".encode("utf-8")]

    def _parse_form_data(self, environ: dict) -> dict[str, list[str]]:
        body_size = int(environ.get("CONTENT_LENGTH") or 0)
        raw_body = environ.get("wsgi.input", BytesIO()).read(body_size)
        return parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)

    def _session_location(self, session: LessonSession) -> str:
        if session.page_kind == "intro":
            return f"/levels/{session.topic.topic_id}"
        if session.page_kind == "revision":
            return f"/levels/{session.topic.topic_id}/revision"
        if session.lesson is None:
            # Added log for debugging the 'rollback' behavior
            print(f"[DEBUG] _session_location: session.lesson is None for page_kind '{session.page_kind}'")
            raise ValueError("Lesson session did not include a lesson.")
        return f"/lessons/{session.lesson.lesson_id}"

    def _render_dashboard(self) -> str:
        dashboard = self.learning_service.build_dashboard(DEFAULT_USER_ID)
        next_topic = dashboard.next_topic.title if dashboard.next_topic is not None else "Roadmap complete"
        active_lesson = ""
        if dashboard.active_lesson is not None:
            active_lesson = (
                f"<div class='callout'><strong>Resume available:</strong> "
                f"<a href='/lessons/{escape(dashboard.active_lesson.lesson_id)}'>"
                f"{escape(dashboard.active_lesson.topic)}</a></div>"
            )
        topic_summary = ""
        if dashboard.current_topic_summary is not None:
            topic_summary = (
                f"<p>Current level average: <strong>{dashboard.current_topic_summary.average_score:.0f}%</strong> "
                f"across {dashboard.current_topic_summary.attempts} question set(s).</p>"
            )
        pending_note = ""
        if dashboard.pending_incorrect_count > 0:
            pending_note = (
                f"<p class='callout'><strong>{dashboard.pending_incorrect_count}</strong> previously incorrect question(s) "
                f"still need a later correct answer before this level can advance.</p>"
            )
        wordbank_link = f"<a class='secondary' href='/wordbank'>Wordbank ({dashboard.wordbank_size})</a>"
        lessons_html = "".join(
            f"<li><a href='/lessons/{escape(lesson.lesson_id)}'>{escape(lesson.topic)}</a> "
            f"<span>Level {lesson.level} / {lesson.cefr_band.value} / difficulty {lesson.difficulty}</span></li>"
            for lesson in dashboard.recent_lessons
        ) or "<li>No lessons served yet.</li>"
        attempts_html = "".join(
            f"<li>{attempt.score_percent:.0f}% on {escape(attempt.lesson_id)}</li>"
            for attempt in dashboard.recent_attempts
        ) or "<li>No quiz attempts yet.</li>"
        roadmap_html = "".join(
            f"<tr><td>{entry.level}</td><td>{escape(entry.title)}</td><td>{escape(entry.cefr_band)}</td>"
            f"<td>{entry.mastery_percent}%</td><td>{escape(entry.status)}</td></tr>"
            for entry in dashboard.roadmap_entries
        )
        return self._page(
            "Lumina Romana",
            f"""
            <section class="hero">
              <div>
                <p class="eyebrow">Adaptive Romanian grammar trainer</p>
                <h1>Lesson loop ready</h1>
                <p>Current CEFR estimate: <strong>{escape(dashboard.user_progress.current_cefr_band.value)}</strong>.
                Next recommended action: <strong>{escape(dashboard.recommended_action)}</strong>.
                Next roadmap topic: <strong>{escape(next_topic)}</strong>.</p>
                {topic_summary}
                {pending_note}
                <form method="post" action="/sessions/start">
                  <button type="submit">Start or resume session</button>
                  <a class="secondary" href="/progress">View progress</a>
                  {wordbank_link}
                </form>
                {active_lesson}
              </div>
            </section>
            <section class="grid">
              <article class="panel">
                <h2>Recent lessons</h2>
                <ul>{lessons_html}</ul>
              </article>
              <article class="panel">
                <h2>Recent quiz performance</h2>
                <ul>{attempts_html}</ul>
              </article>
            </section>
            <section class="panel">
              <h2>Roadmap progress</h2>
              <table>
                <thead><tr><th>Level</th><th>Topic</th><th>Band</th><th>Mastery</th><th>Status</th></tr></thead>
                <tbody>{roadmap_html}</tbody>
              </table>
            </section>
            """,
        )

    def _render_level_intro(self, topic_id: str) -> str:
        intro = self.learning_service.build_level_intro(DEFAULT_USER_ID, topic_id)
        principles_html = "".join(f"<li>{escape(item)}</li>" for item in intro.principles)
        summary_markup = ""
        if intro.summary is not None:
            summary_markup = (
                f"<p>Current average for this level: <strong>{intro.summary.average_score:.0f}%</strong> "
                f"over {intro.summary.attempts} question set(s). Latest page: {intro.summary.latest_score:.0f}%.</p>"
            )
        return self._page(
            intro.topic.title,
            f"""
            <section class="hero">
              <div>
                <p class="eyebrow">Level {intro.topic.level} / {intro.topic.cefr_band.value}</p>
                <h1>{escape(intro.topic.title)}</h1>
                <p>{escape(intro.topic.description)}</p>
                {summary_markup}
                <form method="post" action="/levels/{escape(intro.topic.topic_id)}/begin">
                  <button type="submit">Open revision page</button>
                  <a class="secondary" href="/progress">View progress</a>
                  <a class="secondary" href="/wordbank">Wordbank</a>
                </form>
              </div>
            </section>
            <section class="panel">
              <h2>What this level teaches</h2>
              <ul>{principles_html}</ul>
            </section>
            """,
        )

    def _render_level_revision(self, topic_id: str) -> str:
        revision = self.learning_service.build_level_revision(DEFAULT_USER_ID, topic_id)
        summary_markup = ""
        if revision.summary is not None:
            summary_markup = (
                f"<p>Current average for this level: <strong>{revision.summary.average_score:.0f}%</strong> "
                f"over {revision.summary.attempts} question set(s). Latest page: {revision.summary.latest_score:.0f}%.</p>"
            )
        vocabulary_html = "".join(
            f"<li><strong>{escape(word)}</strong><span>{escape(gloss)}</span></li>"
            for word, gloss in revision.vocabulary
        ) or "<li>No curated vocabulary is available for this level yet.</li>"
        return self._page(
            f"{revision.topic.title} revision",
            f"""
            <section class="hero">
              <div>
                <p class="eyebrow">Revision before Level {revision.topic.level}</p>
                <h1>{escape(revision.topic.title)} vocabulary</h1>
                <p>Review these words before you start this question set. This revision page is available before every set at this level.</p>
                {summary_markup}
                <form method="post" action="/levels/{escape(revision.topic.topic_id)}/practice">
                  <button type="submit">Start question set</button>
                  <a class="secondary" href="/levels/{escape(revision.topic.topic_id)}">Back to level overview</a>
                  <a class="secondary" href="/wordbank">Wordbank</a>
                </form>
              </div>
            </section>
            <section class="panel">
              <h2>Revision vocabulary</h2>
              <ul>{vocabulary_html}</ul>
            </section>
            """,
        )

    def _render_progress(self) -> str:
        dashboard = self.learning_service.build_dashboard(DEFAULT_USER_ID)
        return self._page("Progress", self._progress_markup(dashboard))

    def _render_wordbank(self, query: str) -> str:
        wordbank = self.learning_service.build_wordbank(DEFAULT_USER_ID, query=query)
        entries_html = "".join(
            f"<li><strong>{escape(entry.word)}</strong><span>{escape(entry.definition)}</span><em>{escape(entry.topic.replace('_', ' '))}</em></li>"
            for entry in wordbank.entries
        ) or "<li>No matching wordbank entries yet.</li>"
        return self._page(
            "Wordbank",
            f"""
            <section class="hero">
              <div>
                <p class="eyebrow">Learner wordbank</p>
                <h1>Saved vocabulary</h1>
                <p>Words are added here when a level revision page introduces them.</p>
                <form method="get" action="/wordbank">
                  <label><span>Search</span><input type="text" name="q" value="{escape(wordbank.query)}"></label>
                  <button type="submit">Search</button>
                  <a class="secondary" href="/">Back to dashboard</a>
                </form>
              </div>
            </section>
            <section class="panel">
              <h2>Wordbank entries</h2>
              <ul class="wordbank">{entries_html}</ul>
            </section>
            """,
        )

    def _render_lesson(self, lesson_id: str) -> str:
        lesson = self.learning_service.lesson_repository.get(lesson_id)
        if lesson is None:
            return self._render_not_found()
        examples_html = "".join(
            f"<li><strong>{escape(sentence.romanian)}</strong><span>{escape(sentence.english)}</span></li>"
            for sentence in lesson.example_sentences
        )
        rules_html = "".join(f"<li>{escape(rule)}</li>" for rule in lesson.key_rules)
        questions_html = "".join(
            self._render_question_block(question)
            for question in lesson.quiz_questions
        )
        summary = self.learning_service.topic_attempt_summary(DEFAULT_USER_ID, lesson.topic)
        summary_markup = ""
        if summary is not None and summary.attempts > 0:
            summary_markup = (
                f"<p class='callout'>Current topic average before this page: {summary.average_score:.0f}% "
                f"across {summary.attempts} completed set(s).</p>"
            )
        return self._page(
            lesson.topic,
            f"""
            <section class="hero">
              <div>
                <p class="eyebrow">Level {lesson.level} / {lesson.cefr_band.value} / difficulty {lesson.difficulty}</p>
                <h1>{escape(lesson.topic.replace("_", " ").title())}</h1>
                <p>{escape(lesson.explanation_text)}</p>
                {summary_markup}
                <a class="secondary" href="/levels/{escape(lesson.topic)}/revision">Revision page</a>
                <a class="secondary" href="/wordbank">Wordbank</a>
              </div>
            </section>
            <section class="grid">
              <article class="panel">
                <h2>Worked examples</h2>
                <ul class="examples">{examples_html}</ul>
              </article>
              <article class="panel">
                <h2>Key rules</h2>
                <ul>{rules_html}</ul>
              </article>
            </section>
            <section class="panel">
              <h2>Question set</h2>
              <form method="post" action="/lessons/{escape(lesson.lesson_id)}/submit">
                {questions_html}
                <button type="submit">Submit answers</button>
              </form>
            </section>
            """,
        )

    def _render_result(self, result: QuizResult) -> str:
        feedback_html = "".join(
            (
                f"<article class='feedback {'correct' if item.is_correct else 'incorrect'}'>"
                f"<h3><span class='mark' aria-hidden='true'>{'&#10003;' if item.is_correct else '&#10007;'}</span> "
                f"{escape(item.prompt)}</h3>"
                f"<p class='status'><strong>{'Correct' if item.is_correct else 'Incorrect'}</strong></p>"
                f"<p><strong>Your answer:</strong> {escape(item.submitted_answer or '(blank)')}</p>"
                f"<p><strong>Correct answer:</strong> {escape(item.correct_answer)}</p>"
                f"<p>{escape(item.explanation)}</p>"
                f"{f"<p><strong>Why this was wrong:</strong> {escape(item.why_wrong)}</p>" if item.why_wrong else ''}"
                f"</article>"
            )
            for item in result.feedback
        )
        next_topic = result.next_topic.title if result.next_topic is not None else "Roadmap complete"
        mode_note = ""
        if result.action == "practice":
            mode_note = "<p>This was a practice replay. Your stored mastery and current roadmap position were not changed.</p>"
        elif result.pending_incorrect_count > 0:
            mode_note = (
                f"<p><strong>{result.pending_incorrect_count}</strong> previously incorrect question(s) remain unresolved. "
                "The app will serve those questions again before this level can advance.</p>"
            )
        primary_button_label = "Try another question set"
        if result.action == "advance":
            primary_button_label = "Continue to next level"
        elif result.action == "remediation":
            primary_button_label = "Retry missed questions"
        return self._page(
            "Quiz results",
            f"""
            <section class="hero">
              <div>
                <p class="eyebrow">Question set scored</p>
                <h1>{result.score_percent:.0f}%</h1>
                <p>{result.correct_answers} of {result.total_questions} correct. Running level average:
                <strong>{result.average_score_percent:.0f}%</strong> across {result.topic_attempts} set(s).
                Adaptive follow-up: <strong>{escape(result.action)}</strong>.
                Next topic target: <strong>{escape(next_topic)}</strong>.</p>
                {mode_note}
                <p>You only move on after five completed question sets for this level, with at least 80% on the current set and an 80% or higher average across all sets.</p>
                <div class="actions">
                  <form method="post" action="/sessions/start">
                    <button type="submit">{primary_button_label}</button>
                  </form>
                  <a class="secondary" href="/progress">View progress</a>
                  <a class="secondary" href="/wordbank">Wordbank</a>
                </div>
              </div>
            </section>
            <section class="panel">
              <h2>Answer explanations</h2>
              {feedback_html}
            </section>
            """,
        )

    def _render_not_found(self) -> str:
        return self._page(
            "Not found",
            "<section class='panel'><h1>Page not found</h1><p>The requested page does not exist.</p></section>",
        )

    def _render_question_block(self, question: Question) -> str:
        question_id = question.question_id
        options = question.options
        hint = question.hint
        prompt_markup = self._format_prompt(question.prompt)
        rubric_markup = ""
        if question.rubric:
            rubric_markup = (
                    "<div class='rubric'><strong>Scoring focus</strong><ul>"
                    + "".join(
                f"<li><strong>{escape(name.replace('_', ' ').title())}</strong>: {escape(description)}</li>"
                for name, description in question.rubric.items()
            )
                    + "</ul></div>"
            )
        if options:
            fields = "".join(
                f"<label class='option'><input type='radio' name='answer_{escape(question_id)}' value='{escape(option)}'>"
                f"<span>{escape(option)}</span></label>"
                for option in options
            )
        elif question.question_type == QuestionType.GUIDED_WRITING:
            fields = self._render_response_field(
                question_id,
                label="Your response",
                multiline=True,
                rows=6,
                placeholder="Write two or three connected Romanian sentences.",
            )
        else:
            fields = self._render_response_field(question_id, label="Your answer")
        hint_markup = f"<p class='hint'>Hint: {escape(hint)}</p>" if hint else ""
        task_label = self._question_type_label(question.question_type)
        return (
            f"<fieldset class='question {escape(question.question_type.value)}'>"
            f"<legend><span class='task-type'>{escape(task_label)}</span>{prompt_markup}</legend>"
            f"{rubric_markup}{fields}{hint_markup}</fieldset>"
        )

    def _render_response_field(
        self,
        question_id: str,
        *,
        label: str,
        multiline: bool = False,
        rows: int = 6,
        placeholder: str = "",
    ) -> str:
        field_id = f"answer-field-{question_id}"
        escaped_field_id = escape(field_id)
        escaped_question_id = escape(question_id)
        escaped_placeholder = escape(placeholder)
        if multiline:
            field_markup = (
                f"<textarea id='{escaped_field_id}' name='answer_{escaped_question_id}' rows='{rows}' "
                f"placeholder='{escaped_placeholder}' data-romanian-input='true'></textarea>"
            )
        else:
            field_markup = (
                f"<input id='{escaped_field_id}' type='text' name='answer_{escaped_question_id}' "
                f"placeholder='{escaped_placeholder}' data-romanian-input='true'>"
            )
        return (
            "<div class='response-field'>"
            f"<label for='{escaped_field_id}'><span>{escape(label)}</span>{field_markup}</label>"
            f"{self._render_romanian_character_toolbar(field_id)}"
            "</div>"
        )

    def _render_romanian_character_toolbar(self, target_id: str) -> str:
        keys = "".join(
            f"<button type='button' class='romanian-key' data-romanian-char='{escape(character)}' "
            f"data-target='{escape(target_id)}' aria-label='Insert {escape(character)}'>{escape(character)}</button>"
            for character in ROMANIAN_CHARACTERS
        )
        return (
            f"<div class='romanian-toolbar' data-romanian-toolbar='true' data-target='{escape(target_id)}'>"
            "<span class='toolbar-label'>Romanian characters</span>"
            f"{keys}</div>"
        )

    def _format_prompt(self, prompt: str) -> str:
        if "'" in prompt:
            parts = prompt.split("'")
            formatted: list[str] = []
            for index, part in enumerate(parts):
                cleaned = part.strip()
                if not cleaned:
                    continue
                if index % 2 == 1:
                    formatted.append(f"<blockquote>{escape(cleaned)}</blockquote>")
                else:
                    formatted.append(f"<span>{escape(cleaned)}</span>")
            return "".join(formatted)
        return f"<span>{escape(prompt)}</span>"

    def _question_type_label(self, question_type: QuestionType) -> str:
        labels = {
            QuestionType.MULTIPLE_CHOICE: "Multiple choice",
            QuestionType.ENGLISH_TO_ROMANIAN: "Translate to Romanian",
            QuestionType.ROMANIAN_TO_ENGLISH: "Translate to English",
            QuestionType.FILL_IN_THE_BLANK: "Fill in the blank",
            QuestionType.ERROR_IDENTIFICATION: "Error identification",
            QuestionType.SENTENCE_TRANSFORMATION: "Sentence transformation",
            QuestionType.GUIDED_WRITING: "Guided writing",
            QuestionType.READING_COMPREHENSION: "Reading comprehension",
            QuestionType.DIALOGUE_COMPLETION: "Dialogue completion",
        }
        return labels[question_type]

    def _progress_markup(self, dashboard: DashboardData) -> str:
        recent_scores = ", ".join(f"{score:.0f}%" for score in dashboard.user_progress.recent_scores) or "No scores yet"
        skill_scores = dashboard.user_progress.skill_scores
        topic_summary = ""
        if dashboard.current_topic_summary is not None:
            topic_summary = (
                f"<p>Current topic average: {dashboard.current_topic_summary.average_score:.0f}% "
                f"over {dashboard.current_topic_summary.attempts} set(s).</p>"
            )
        pending_summary = ""
        if dashboard.pending_incorrect_count > 0:
            pending_summary = (
                f"<p><strong>{dashboard.pending_incorrect_count}</strong> previously incorrect question(s) are still blocking advancement.</p>"
            )
        skill_markup = "".join(
            f"<li><strong>{escape(skill_name.replace('_', ' ').title())}</strong><span>{score:.0f}% support signal</span></li>"
            for skill_name, score in sorted(skill_scores.items())
        ) or "<li>No upper-level skill signals recorded yet.</li>"
        mastery_cards = "".join(
            (
                f"<li><strong>{escape(entry.title)}</strong><span>{entry.mastery_percent}% mastery</span>"
                f"<em>{escape(entry.status)}</em>"
                f"{self._revisit_button(entry, dashboard)}"
                f"</li>"
            )
            for entry in dashboard.roadmap_entries
        )
        attempts_html = "".join(
            f"<li>{attempt.score_percent:.0f}% on {escape(attempt.lesson_id)}</li>"
            for attempt in dashboard.recent_attempts
        ) or "<li>No attempts yet.</li>"
        return f"""
        <section class="hero">
          <div>
            <p class="eyebrow">Learner progress</p>
            <h1>{escape(dashboard.user_progress.current_cefr_band.value)}</h1>
            <p>Current level {dashboard.user_progress.current_level}, difficulty {dashboard.user_progress.current_difficulty},
            total XP {dashboard.user_progress.total_xp}.</p>
            <p>Recent scores: {escape(recent_scores)}.</p>
            {topic_summary}
            {pending_summary}
            <a class="secondary" href="/">Back to dashboard</a>
            <a class="secondary" href="/wordbank">Wordbank</a>
          </div>
        </section>
        <section class="grid">
          <article class="panel">
            <h2>Current roadmap state</h2>
            <ul class="mastery">{mastery_cards}</ul>
          </article>
          <article class="panel">
            <h2>Recent attempts</h2>
            <ul>{attempts_html}</ul>
          </article>
          <article class="panel">
            <h2>Skill signals</h2>
            <ul class="mastery">{skill_markup}</ul>
          </article>
        </section>
        """

    def _revisit_button(self, entry, dashboard: DashboardData) -> str:
        if entry.level > dashboard.user_progress.current_level:
            return ""
        return (
            f"<form method='post' action='/progress/revisit' class='inline-form'>"
            f"<input type='hidden' name='topic_id' value='{escape(entry.topic_id)}'>"
            f"<button type='submit'>Redo level</button>"
            f"</form>"
        )

    def _runtime_mode_banner(self) -> str:
        if not self.application.settings.ai.offline_only:
            return ""
        return (
            "<section class='mode-banner'>"
            "<strong>Offline-only mode active.</strong> "
            "This server uses cached or deterministic local questions only and will not call an AI provider."
            "</section>"
        )

    def _page(self, title: str, body: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} | Lumina Romana</title>
  <style>
    :root {{
      --bg: #f6f1e7;
      --paper: #fffdf8;
      --ink: #1f2421;
      --muted: #6d645a;
      --accent: #af3e2f;
      --accent-dark: #7f2b20;
      --line: #d8cbb6;
      --ok: #285943;
      --warn: #8a3f2a;
      font-family: Georgia, "Palatino Linotype", serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; color: var(--ink); background:
      radial-gradient(circle at top left, rgba(175,62,47,.16), transparent 32rem),
      linear-gradient(180deg, #f3ecdd 0%, #f8f4eb 55%, #f1e7d7 100%);
    }}
    a {{ color: var(--accent-dark); }}
    main {{ max-width: 1080px; margin: 0 auto; padding: 2rem 1.25rem 3rem; }}
    .hero, .panel {{ background: rgba(255,253,248,.88); border: 1px solid var(--line); border-radius: 22px; box-shadow: 0 18px 40px rgba(74,52,34,.08); }}
    .hero {{ padding: 2rem; margin-bottom: 1.5rem; }}
    .panel {{ padding: 1.5rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }}
    h1, h2, h3 {{ margin-top: 0; }}
    .eyebrow {{ text-transform: uppercase; letter-spacing: .12em; color: var(--muted); font-size: .82rem; }}
    button, .secondary {{
      display: inline-block; border-radius: 999px; padding: .8rem 1.2rem; text-decoration: none; border: 0;
      background: var(--accent); color: white; font-weight: 700; cursor: pointer;
    }}
    .secondary {{ background: transparent; border: 1px solid var(--line); color: var(--ink); margin-left: .5rem; }}
    form {{ margin: 0; }}
    ul {{ padding-left: 1.1rem; }}
    li {{ margin-bottom: .65rem; }}
    li span, li em {{ display: block; color: var(--muted); font-style: normal; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: .7rem .5rem; border-bottom: 1px solid var(--line); text-align: left; }}
    .question {{ border: 1px solid var(--line); border-radius: 16px; padding: 1rem; margin-bottom: 1rem; }}
    .task-type {{ display: inline-block; margin-right: .65rem; padding: .18rem .55rem; border-radius: 999px; background: rgba(175,62,47,.12); color: var(--accent-dark); font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; }}
    .option, .question label {{ display: block; margin: .45rem 0; }}
    input[type=text], textarea {{ width: 100%; padding: .7rem .8rem; border-radius: 12px; border: 1px solid var(--line); background: white; font: inherit; }}
    textarea {{ resize: vertical; min-height: 8rem; }}
    .response-field {{ display: grid; gap: .55rem; }}
    .romanian-toolbar {{
      display: flex;
      flex-wrap: wrap;
      gap: .4rem;
      align-items: center;
      padding: .65rem .75rem;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(175,62,47,.05);
    }}
    .toolbar-label {{ color: var(--muted); font-size: .88rem; margin-right: .25rem; }}
    .romanian-key {{
      min-width: 2.25rem;
      padding: .45rem .7rem;
      border-radius: 10px;
      border: 1px solid rgba(175,62,47,.22);
      background: white;
      color: var(--accent-dark);
      font-weight: 700;
    }}
    blockquote {{ margin: .7rem 0; padding: .8rem 1rem; border-left: 4px solid var(--accent); background: rgba(175,62,47,.06); }}
    .rubric {{ margin-bottom: .8rem; padding: .75rem .85rem; border-radius: 14px; background: rgba(31,36,33,.04); border: 1px solid var(--line); }}
    .rubric ul {{ margin: .45rem 0 0; }}
    .hint, .callout {{ color: var(--muted); }}
    .feedback {{ border-radius: 16px; padding: 1rem; margin-bottom: 1rem; border: 1px solid var(--line); }}
    .feedback.correct {{ background: rgba(40,89,67,.08); border-color: rgba(40,89,67,.24); }}
    .feedback.incorrect {{ background: rgba(138,63,42,.08); border-color: rgba(138,63,42,.22); }}
    .mark {{ display: inline-block; min-width: 1.25rem; font-weight: 700; }}
    .feedback.correct .mark, .feedback.correct .status {{ color: var(--ok); }}
    .feedback.incorrect .mark, .feedback.incorrect .status {{ color: var(--warn); }}
    .mode-banner {{
      margin: 0 auto 1rem;
      padding: .9rem 1rem;
      border-radius: 16px;
      border: 1px solid rgba(138,63,42,.24);
      background: rgba(138,63,42,.08);
      color: var(--warn);
    }}
    .actions {{ display: flex; flex-wrap: wrap; gap: .75rem; align-items: center; }}
    .mastery {{ list-style: none; padding-left: 0; }}
    .mastery li {{ padding: .75rem 0; border-bottom: 1px solid var(--line); }}
    .inline-form {{ margin-top: .6rem; }}
    .inline-form button {{ padding: .55rem .95rem; font-size: .92rem; }}
    .wordbank li {{ padding: .75rem 0; border-bottom: 1px solid var(--line); }}
    @media (max-width: 720px) {{
      .hero, .panel {{ padding: 1.1rem; border-radius: 18px; }}
      .secondary {{ margin-left: 0; }}
      .actions {{ flex-direction: column; align-items: stretch; }}
    }}
  </style>
</head>
<body>
  <main>{self._runtime_mode_banner()}{body}</main>
  <script>
    document.addEventListener("click", function(event) {{
      var button = event.target.closest("[data-romanian-char]");
      if (!button) {{
        return;
      }}
      var targetId = button.getAttribute("data-target");
      var character = button.getAttribute("data-romanian-char") || "";
      var field = targetId ? document.getElementById(targetId) : null;
      if (!field) {{
        return;
      }}
      event.preventDefault();
      var start = typeof field.selectionStart === "number" ? field.selectionStart : field.value.length;
      var end = typeof field.selectionEnd === "number" ? field.selectionEnd : field.value.length;
      var prefix = field.value.slice(0, start);
      var suffix = field.value.slice(end);
      field.value = prefix + character + suffix;
      var nextCaret = start + character.length;
      field.focus();
      if (typeof field.setSelectionRange === "function") {{
        field.setSelectionRange(nextCaret, nextCaret);
      }}
      field.dispatchEvent(new Event("input", {{ bubbles: true }}));
    }});
  </script>
</body>
</html>"""

    def _html_response(self, body: str, *, status: str = "200 OK") -> HTMLResponse:
        return status, [("Content-Type", "text/html; charset=utf-8")], body.encode("utf-8")

    def _redirect(self, location: str) -> HTMLResponse:
        return "302 Found", [("Location", location)], b""


def create_web_app(application: Application) -> WebApp:
    return WebApp(application=application, learning_service=application.learning_service)


def run_dev_server(application: Application) -> None:
    web_app = create_web_app(application)
    with make_server(application.settings.web.host, application.settings.web.port, web_app) as server:
        if application.settings.ai.offline_only:
            application.logger.info(
                "Starting web server in offline-only mode on http://%s:%s",
                application.settings.web.host,
                application.settings.web.port,
            )
            print(
                "Serving Lumina Romana in offline-only mode on "
                f"http://{application.settings.web.host}:{application.settings.web.port}"
            )
        else:
            application.logger.info(
                "Starting web server on http://%s:%s",
                application.settings.web.host,
                application.settings.web.port,
            )
            print(f"Serving Lumina Romana on http://{application.settings.web.host}:{application.settings.web.port}")
        server.serve_forever()
