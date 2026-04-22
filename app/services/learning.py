"""Learning service: orchestration of lesson flow and user progress.

Central service responsible for starting lessons, handling quiz attempts, and
tracking learner progress and mastery interactions.
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata
import traceback
from collections.abc import Mapping
from dataclasses import dataclass
from statistics import mean
from uuid import uuid4

from app.ai.service import AIService
from app.ai.types import LessonGenerationRequest
from app.models import CEFRBand, Lesson, Question, QuizAttempt, TopicMetadata, UserProgress, WordbankEntry, VerbbankEntry
from app.storage import LessonRepository, QuizAttemptRepository, UserProgressRepository, WordbankRepository, VerbbankRepository

from .difficulty import DifficultyManager, SessionAction
from .roadmap import ContentLibrary

DEFAULT_USER_ID = "default-learner"
PASSING_SCORE = 80.0
MIN_ATTEMPTS_TO_ADVANCE = 5
QUESTION_SET_COOLDOWN = 5
WORD_TOKEN_PATTERN = re.compile(r"[A-Za-zĂÂÎȘȚăâîșțŞŢşţ]+(?:[-'][A-Za-zĂÂÎȘȚăâîșțŞŢşţ]+)*")

LEVEL_PRINCIPLES: dict[str, tuple[str, ...]] = {
    "romanian_basics": (
        "Romanian spelling matters because letters with diacritics are different letters, not decorative marks. For example, 'a', 'ă', 'â', and 'î' signal different sounds and often different words.",
        "This level introduces the verb 'a fi' meaning 'to be', because Romanian uses it constantly in identity and description sentences such as 'Eu sunt student' for 'I am a student'.",
        "You will also see that Romanian learner phrases often omit the indefinite article where English uses 'a', so 'Eu sunt student' is natural even though English says 'I am a student'.",
    ),
    "nouns_and_articles": (
        "Romanian usually puts the definite article at the end of the noun instead of using a separate word before it. That is why 'băiat' becomes 'băiatul' for 'the boy'.",
        "The ending '-ul' is a common masculine singular definite ending. It signals that the noun is specific, doing the job that English 'the' would do.",
        "Different noun genders behave differently, so this level helps you see why some nouns change visibly in the definite form while others change less or in a different way.",
    ),
    "core_cases": (
        "Romanian changes noun forms to show grammatical relationships such as possession, giving, or receiving. Those form changes are part of the case system.",
        "You will meet forms like 'lui' and endings such as '-ului'. In beginner Romanian, 'lui' often helps express possession or relation, similar to 'of' or 'to' in English depending on context.",
        "A phrase like 'cartea băiatului' literally marks 'the boy' in a genitive-style form, so the ending tells you the book belongs to the boy.",
    ),
    "present_tense_verbs": (
        "Romanian verbs change with the subject, so the ending tells you who is doing the action. That is why 'eu învăț' and 'noi învățăm' cannot use the same verb form.",
        "These endings are not optional decoration. They carry person and number information, which is why subject-verb agreement is central in Romanian sentence building.",
        "You are learning to recognise common present-tense patterns first so later tense work feels like an extension of a system rather than a list of isolated phrases.",
    ),
    "pronouns_and_tenses": (
        "Romanian pronouns often sit close to the verb, and small forms such as 'îl' or 'o' can carry a lot of meaning, replacing whole noun phrases once the context is clear.",
        "This level also introduces compound tense building, where an auxiliary such as 'am' combines with a participle to express completed past actions.",
        "Understanding these short helper words is important because Romanian often packs tense and object information into compact verb groups.",
    ),
    "connected_communication": (
        "Here the focus shifts from isolated sentences to linked everyday communication, so you start seeing how Romanian uses sequencing words to join events into a clear flow.",
        "Imperatives matter because Romanian uses short verb forms for direct instructions, and those forms help you sound natural in requests and commands.",
        "Comparative adverbs such as 'mai repede' show how Romanian expresses comparison through structures that literally mean 'more quickly', which is an important pattern to internalise.",
    ),
    "narrative_b1_grammar": (
        "B1 Romanian starts asking you to connect events, not just solve single isolated sentence drills. That means you need to control how background information and completed actions work together in a short narrative.",
        "A contrast such as imperfect versus perfect compound helps the listener understand whether an action was ongoing background or a finished event that moved the story forward.",
        "You also begin using relative clauses and practical obligation structures so grammar supports realistic descriptions, messages, and plans.",
    ),
    "b1_b2_transition": (
        "This stage broadens Romanian from core narrative control into polite requests, hypotheticals, and denser clause linking that appears in everyday work, travel, and service interactions.",
        "Conditional forms such as 'as dori' and 'as vrea' matter because they let you sound natural and appropriately polite instead of overly direct.",
        "You are also learning to hold longer clause chains together, which means pronoun placement and connectors must remain clear across connected ideas.",
    ),
}


@dataclass(frozen=True, slots=True)
class TopicAttemptSummary:
    topic_id: str
    attempts: int
    average_score: float
    latest_score: float | None
    page_passed: bool
    topic_passed: bool


@dataclass(frozen=True, slots=True)
class RoadmapProgressEntry:
    level: int
    topic_id: str
    title: str
    cefr_band: str
    mastery_percent: int
    status: str


@dataclass(frozen=True, slots=True)
class DashboardData:
    user_progress: UserProgress
    next_topic: TopicMetadata | None
    active_lesson: Lesson | None
    recommended_action: str
    recent_lessons: tuple[Lesson, ...]
    recent_attempts: tuple[QuizAttempt, ...]
    roadmap_entries: tuple[RoadmapProgressEntry, ...]
    current_topic_summary: TopicAttemptSummary | None
    pending_incorrect_count: int
    wordbank_size: int
    verbbank_size: int


@dataclass(frozen=True, slots=True)
class LevelIntro:
    topic: TopicMetadata
    principles: tuple[str, ...]
    summary: TopicAttemptSummary | None
    session_goal: str


@dataclass(frozen=True, slots=True)
class LevelRevision:
    topic: TopicMetadata
    vocabulary: tuple[tuple[str, str], ...]
    summary: TopicAttemptSummary | None
    session_goal: str


@dataclass(frozen=True, slots=True)
class LessonSession:
    page_kind: str
    topic: TopicMetadata
    session_goal: str
    resumed: bool
    source: str
    lesson: Lesson | None = None
    warnings: tuple[str, ...] = ()
    level_intro: LevelIntro | None = None
    level_revision: LevelRevision | None = None


@dataclass(frozen=True, slots=True)
class QuestionFeedback:
    question_id: str
    prompt: str
    correct_answer: str
    submitted_answer: str
    explanation: str
    why_wrong: str | None
    is_correct: bool
    tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QuizResult:
    lesson: Lesson
    score_percent: float
    average_score_percent: float
    correct_answers: int
    total_questions: int
    action: str
    next_topic: TopicMetadata | None
    topic_attempts: int
    topic_passed: bool
    pending_incorrect_count: int
    feedback: tuple[QuestionFeedback, ...]
    updated_progress: UserProgress


@dataclass(frozen=True, slots=True)
class WordbankData:
    query: str
    entries: tuple[WordbankEntry, ...]


@dataclass(frozen=True, slots=True)
class VerbbankData:
    query: str
    entries: tuple[VerbbankEntry, ...]


class InMemoryVerbbankRepository:
    """A tiny in-memory VerbbankRepository used as a default when no repository is provided.

    It implements the minimal methods used by the service: upsert, search_for_user and delete_for_user.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict[str, VerbbankEntry]] = {}

    def upsert(self, entry: VerbbankEntry) -> None:
        user = self._store.setdefault(entry.user_id, {})
        user[entry.verb] = entry

    def search_for_user(self, user_id: str, query: str = "", limit: int = 100) -> list[VerbbankEntry]:
        entries = list(self._store.get(user_id, {}).values())
        if query.strip():
            q = query.strip().casefold()
            entries = [
                e for e in entries
                if q in e.verb.casefold() or q in e.conjugations.casefold() or q in e.topic.casefold()
            ]
        entries.sort(key=lambda e: e.verb)
        return entries[:limit]

    def delete_for_user(self, user_id: str) -> None:
        self._store.pop(user_id, None)


@dataclass(frozen=True, slots=True)
class PlacementOutcome:
    cefr_band: str
    suggested_level: int
    suggested_topic_id: str
    section_scores: dict[str, float]
    rationale: tuple[str, ...]


class LearningService:
    def __init__(
            self,
            *,
            user_progress_repository: UserProgressRepository,
            lesson_repository: LessonRepository,
            quiz_attempt_repository: QuizAttemptRepository,
            wordbank_repository: WordbankRepository,
            verbbank_repository: VerbbankRepository | None = None,
            content_library: ContentLibrary,
            difficulty_manager: DifficultyManager,
            ai_service: AIService,
    ) -> None:
        self.user_progress_repository = user_progress_repository
        self.lesson_repository = lesson_repository
        self.quiz_attempt_repository = quiz_attempt_repository
        self.wordbank_repository = wordbank_repository
        # Allow tests and callers to omit a verbbank repository; provide a small in-memory default.
        self.verbbank_repository = verbbank_repository or InMemoryVerbbankRepository()
        self.content_library = content_library
        self.difficulty_manager = difficulty_manager
        self.ai_service = ai_service

    def get_or_create_user_progress(self, user_id: str = DEFAULT_USER_ID) -> UserProgress:
        progress = self.user_progress_repository.get(user_id)
        if progress is None:
            progress = UserProgress(user_id=user_id)
            self.user_progress_repository.save(progress)
        return progress

    def reset_progress(self, user_id: str = DEFAULT_USER_ID) -> UserProgress:
        self._clear_user_state(user_id)
        progress = UserProgress(user_id=user_id)
        self.user_progress_repository.save(progress)
        return progress

    def set_testing_position(
            self,
            *,
            level: int,
            user_id: str = DEFAULT_USER_ID,
            difficulty: int | None = None,
    ) -> UserProgress:
        topics = self.content_library.all_topics()
        if level < 1 or level > len(topics):
            raise ValueError(f"Level must be between 1 and {len(topics)}.")

        target_topic = next(topic for topic in topics if topic.level == level)
        normalized_difficulty = difficulty if difficulty is not None else level
        if not 1 <= normalized_difficulty <= 10:
            raise ValueError("Difficulty must be between 1 and 10.")

        self._clear_user_state(user_id)
        progress = UserProgress(
            user_id=user_id,
            current_level=level,
            current_cefr_band=target_topic.cefr_band,
            current_difficulty=normalized_difficulty,
        )
        for topic in topics:
            if topic.level < level:
                progress.update_mastery(topic.topic_id, self.difficulty_manager.b2_prerequisite_threshold)

        if target_topic.cefr_band == CEFRBand.B2:
            progress.update_skill_score("grammar", 85.0)
            progress.update_skill_score("integrated_grammar", 82.0)
            progress.update_skill_score("reading", 80.0)
            progress.update_skill_score("writing", 80.0)
        elif target_topic.cefr_band == CEFRBand.B1:
            progress.update_skill_score("grammar", 80.0)
            progress.update_skill_score("integrated_grammar", 78.0)

        self.user_progress_repository.save(progress)
        return progress

    def build_dashboard(self, user_id: str = DEFAULT_USER_ID) -> DashboardData:
        progress = self.get_or_create_user_progress(user_id)
        active_lesson = self.get_active_lesson(user_id)
        recent_lessons = tuple(self.lesson_repository.list_for_user(user_id, limit=6))
        recent_attempts = tuple(self.quiz_attempt_repository.list_for_user(user_id, limit=6))
        remediation_topic = self._next_remediation_topic(user_id)
        next_topic = remediation_topic or self.content_library.next_topic_for_user(progress)

        current_topic_summary = None
        pending_incorrect_count = 0
        if next_topic is not None:
            current_topic_summary = self.topic_attempt_summary(user_id, next_topic.topic_id)
            pending_incorrect_count = len(
                self.quiz_attempt_repository.list_pending_incorrect_questions(
                    user_id,
                    topic_id=next_topic.topic_id,
                )
            )

        recommended_action = "advance"
        if pending_incorrect_count > 0 and current_topic_summary is not None and current_topic_summary.topic_passed:
            recommended_action = "remediation"
        elif current_topic_summary is not None and not current_topic_summary.topic_passed and current_topic_summary.attempts > 0:
            recommended_action = "hold" if current_topic_summary.page_passed else "review"
        elif progress.recent_scores and progress.recent_scores[-1] < PASSING_SCORE:
            recommended_action = "review"

        return DashboardData(
            user_progress=progress,
            next_topic=next_topic,
            active_lesson=active_lesson,
            recommended_action=recommended_action,
            recent_lessons=recent_lessons,
            recent_attempts=recent_attempts,
            roadmap_entries=self._roadmap_entries(progress, next_topic),
            current_topic_summary=current_topic_summary,
            pending_incorrect_count=pending_incorrect_count,
            wordbank_size=len(self.wordbank_repository.search_for_user(user_id, limit=1000)),
            verbbank_size=len(self.verbbank_repository.search_for_user(user_id, limit=1000)),
        )

    def get_active_lesson(self, user_id: str = DEFAULT_USER_ID) -> Lesson | None:
        lessons = self.lesson_repository.list_for_user(user_id, limit=20)
        attempted_lesson_ids = {
            attempt.lesson_id for attempt in self.quiz_attempt_repository.list_for_user(user_id, limit=50)
        }
        for lesson in lessons:
            if (
                lesson.lesson_id not in attempted_lesson_ids
                and self._lesson_is_resume_ready(lesson)
                and not self._lesson_has_non_english_guidance(lesson)
            ):
                return lesson
        return None

    def start_or_resume_session(self, user_id: str = DEFAULT_USER_ID) -> LessonSession:
        active_lesson = self.get_active_lesson(user_id)
        if active_lesson is not None:
            topic = self.content_library.get_topic(active_lesson.topic)
            if topic is None:
                raise ValueError(f"Unknown topic '{active_lesson.topic}'.")
            return LessonSession(
                page_kind="lesson",
                topic=topic,
                lesson=active_lesson,
                session_goal=self._infer_session_goal(user_id, topic.topic_id),
                resumed=True,
                source="history",
                warnings=(),
            )

        progress = self.get_or_create_user_progress(user_id)
        topic = self._next_remediation_topic(user_id) or self.content_library.next_topic_for_user(progress)
        if topic is None:
            topic = self.content_library.all_topics()[-1]

        remediation_session = self._maybe_start_remediation_session(user_id, topic.topic_id)
        if remediation_session is not None:
            return remediation_session

        if self._needs_intro(user_id, topic.topic_id):
            return LessonSession(
                page_kind="intro",
                topic=topic,
                session_goal=self._infer_session_goal(user_id, topic.topic_id),
                resumed=False,
                source="system",
                level_intro=self.build_level_intro(user_id, topic.topic_id),
            )
        return LessonSession(
            page_kind="revision",
            topic=topic,
            session_goal=self._infer_session_goal(user_id, topic.topic_id),
            resumed=False,
                source="system",
                level_revision=self.build_level_revision(user_id, topic.topic_id),
            )

    def start_or_resume_lesson_session(self, user_id: str = DEFAULT_USER_ID) -> LessonSession:
        active_lesson = self.get_active_lesson(user_id)
        if active_lesson is not None:
            topic = self.content_library.get_topic(active_lesson.topic)
            if topic is None:
                raise ValueError(f"Unknown topic '{active_lesson.topic}'.")
            return LessonSession(
                page_kind="lesson",
                topic=topic,
                lesson=active_lesson,
                session_goal=self._infer_session_goal(user_id, topic.topic_id),
                resumed=True,
                source="history",
                warnings=(),
            )

        progress = self.get_or_create_user_progress(user_id)
        topic = self._next_remediation_topic(user_id) or self.content_library.next_topic_for_user(progress)
        if topic is None:
            topic = self.content_library.all_topics()[-1]

        remediation_session = self._maybe_start_remediation_session(user_id, topic.topic_id)
        if remediation_session is not None:
            return remediation_session

        self._record_topic_vocabulary(user_id, topic.topic_id)
        return self.start_topic_lesson(topic.topic_id, user_id=user_id)

    def start_topic_lesson(
            self,
            topic_id: str,
            *,
            user_id: str = DEFAULT_USER_ID,
            session_goal_override: str | None = None,
    ) -> LessonSession:
        """
        Generates a new lesson for a specific topic with explicit logging.
        """
        print(f"\n[DEBUG] LearningService.start_topic_lesson: Starting for {topic_id}", flush=True)

        try:
            progress = self.get_or_create_user_progress(user_id)
            topic = self.content_library.get_topic(topic_id)
            if topic is None:
                print(f"[DEBUG] LearningService: Topic {topic_id} not found.", flush=True)
                raise ValueError(f"Unknown topic '{topic_id}'.")

            session_goal = session_goal_override or self._infer_session_goal(user_id, topic_id)
            focus_tags = self._topic_focus_tags(user_id, topic_id)
            excluded_question_keys = tuple(
                self.quiz_attempt_repository.list_recent_correct_question_keys(
                    user_id,
                    recent_attempt_limit=QUESTION_SET_COOLDOWN,
                )
            )
            avoid_question_prompts = self.quiz_attempt_repository.list_recent_correct_question_prompts(
                user_id,
                recent_attempt_limit=QUESTION_SET_COOLDOWN,
            )

            print(f"[DEBUG] LearningService: Requesting AI generation via AIService...", flush=True)

            result = self.ai_service.generate_lesson(
                LessonGenerationRequest(
                    user_progress=progress,
                    topic_id=topic_id,
                    session_goal=session_goal,
                    focus_tags=focus_tags,
                    avoid_question_prompts=avoid_question_prompts,
                    excluded_question_keys=excluded_question_keys,
                )
            )

            lesson, cooldown_warnings = self._apply_recent_question_cooldown(
                topic_id=topic_id,
                lesson=result.lesson,
                session_goal=session_goal,
                excluded_question_keys=set(excluded_question_keys),
            )
            lesson, dedupe_warnings = self._ensure_unique_questions_in_lesson(
                topic_id=topic_id,
                lesson=lesson,
                session_goal=session_goal,
                excluded_question_keys=set(excluded_question_keys),
            )
            lesson, guidance_warnings = self._ensure_english_guidance_lesson(
                topic_id=topic_id,
                lesson=lesson,
                session_goal=session_goal,
                excluded_question_keys=set(excluded_question_keys),
            )
            if session_goal == "practice" and not self._is_practice_lesson(lesson):
                lesson.lesson_id = f"practice-{topic_id}-{uuid4()}"

            self.lesson_repository.save(user_id, lesson)
            self._record_lesson_vocabulary(user_id, lesson)
            print(f"[DEBUG] LearningService: Session successfully created.", flush=True)

            return LessonSession(
                page_kind="lesson",
                topic=topic,
                session_goal=session_goal,
                resumed=False,
                source=result.source,
                lesson=lesson,
                warnings=(*result.warnings, *cooldown_warnings, *dedupe_warnings, *guidance_warnings),
            )

        except Exception as e:
            print("\n" + "!" * 60)
            print(f"FATAL ERROR IN LearningService.start_topic_lesson")
            print(f"Error Type: {type(e).__name__}")
            print(f"Message: {str(e)}")
            print("-" * 60)
            traceback.print_exc()
            print("!" * 60 + "\n")
            raise

    def build_level_intro(self, user_id: str, topic_id: str) -> LevelIntro:
        topic = self.content_library.get_topic(topic_id)
        if topic is None:
            raise ValueError(f"Unknown topic '{topic_id}'.")
        return LevelIntro(
            topic=topic,
            principles=self._principles_for_topic(topic),
            summary=self.topic_attempt_summary(user_id, topic_id),
            session_goal=self._infer_session_goal(user_id, topic_id),
        )

    def build_level_revision(self, user_id: str, topic_id: str) -> LevelRevision:
        topic = self.content_library.get_topic(topic_id)
        if topic is None:
            raise ValueError(f"Unknown topic '{topic_id}'.")
        self.get_or_create_user_progress(user_id)
        self._record_topic_vocabulary(user_id, topic_id)
        return LevelRevision(
            topic=topic,
            vocabulary=self.content_library.vocabulary_for_topic(topic_id),
            summary=self.topic_attempt_summary(user_id, topic_id),
            session_goal=self._infer_session_goal(user_id, topic_id),
        )

    def build_wordbank(self, user_id: str = DEFAULT_USER_ID, query: str = "") -> WordbankData:
        self.get_or_create_user_progress(user_id)
        entries = list(self.wordbank_repository.search_for_user(user_id, query=query))

        # If AI is configured, enrich entries that lack concise translations.
        try:
            if self.ai_service and self.ai_service.is_configured:
                # Find entries that only have the example-based definition or ambiguous defs
                candidates: list[str] = []
                for entry in entries:
                    if entry.definition.strip().lower().startswith("seen in example:"):
                        candidates.append(entry.word)
                if candidates:
                    glosses = self.ai_service.generate_glosses(candidates)
                    for w, gloss in glosses.items():
                        # Update DB for matching stored word (normalize key)
                        norm = self._normalize_wordbank_text(w)
                        if gloss:
                            try:
                                self.wordbank_repository.update_definition(user_id, norm, gloss)
                            except Exception:
                                # If repository doesn't support update or update fails, skip enrichment for this word
                                pass
                    # Re-read entries after enrichment
                    entries = list(self.wordbank_repository.search_for_user(user_id, query=query))
        except Exception:
            # If AI enrichment fails, ignore and return current entries
            pass

        return WordbankData(
            query=query,
            entries=tuple(entries),
        )

    def build_verbbank(self, user_id: str = DEFAULT_USER_ID, query: str = "") -> VerbbankData:
        self.get_or_create_user_progress(user_id)
        entries = list(self.verbbank_repository.search_for_user(user_id, query=query))
        if self._refresh_verbbank_entries(user_id, entries):
            entries = list(self.verbbank_repository.search_for_user(user_id, query=query))
        return VerbbankData(
            query=query,
            entries=tuple(entries),
        )

    def evaluate_placement(self, section_scores: Mapping[str, float]) -> PlacementOutcome:
        blueprint = self.content_library.placement_blueprint()
        normalized_scores = {
            section.section_id: float(section_scores.get(section.section_id, 0.0))
            for section in blueprint
        }
        rationale = [f"{section.title}: {normalized_scores[section.section_id]:.1f}%" for section in blueprint]

        if (
                normalized_scores.get("placement_b2_integrated_control", 0.0) >= 70.0
                and normalized_scores.get("placement_b1_functional_range", 0.0) >= 70.0
        ):
            suggested_level = 9
        elif normalized_scores.get("placement_b1_functional_range", 0.0) >= 70.0:
            suggested_level = 7
        elif normalized_scores.get("placement_a2_everyday_use", 0.0) >= 70.0:
            suggested_level = 5
        else:
            suggested_level = 1

        topic = next(topic for topic in self.content_library.all_topics() if topic.level == suggested_level)
        rationale.append(
            f"Suggested start is Level {suggested_level} ({topic.cefr_band.value}) because this is the highest section with stable control."
        )
        return PlacementOutcome(
            cefr_band=topic.cefr_band.value,
            suggested_level=suggested_level,
            suggested_topic_id=topic.topic_id,
            section_scores=normalized_scores,
            rationale=tuple(rationale),
        )

    def topic_attempt_summary(self, user_id: str, topic_id: str) -> TopicAttemptSummary | None:
        topic_attempts = self._attempts_for_topic(user_id, topic_id)
        if not topic_attempts:
            return None
        latest_score = topic_attempts[-1].score_percent
        average_score = mean(attempt.score_percent for attempt in topic_attempts)
        page_passed = latest_score >= PASSING_SCORE
        topic_passed = (
                len(topic_attempts) >= MIN_ATTEMPTS_TO_ADVANCE
                and page_passed
                and average_score >= PASSING_SCORE
        )
        return TopicAttemptSummary(
            topic_id=topic_id,
            attempts=len(topic_attempts),
            average_score=round(average_score, 2),
            latest_score=latest_score,
            page_passed=page_passed,
            topic_passed=topic_passed,
        )

    def submit_quiz(
            self,
            lesson_id: str,
            answers: dict[str, str],
            *,
            user_id: str = DEFAULT_USER_ID,
    ) -> QuizResult:
        lesson = self.lesson_repository.get(lesson_id)
        if lesson is None:
            raise ValueError(f"Unknown lesson '{lesson_id}'.")

        progress = self.get_or_create_user_progress(user_id)
        practice_mode = self._is_practice_lesson(lesson)
        prior_topic_summary = self.topic_attempt_summary(user_id, lesson.topic) if practice_mode else None

        feedback: list[QuestionFeedback] = []
        mistake_tags: list[str] = []
        correct_answers = 0

        for question in lesson.quiz_questions:
            submitted_answer = answers.get(question.question_id, "").strip()
            is_correct = self._answers_match(question.correct_answer, submitted_answer)
            why_wrong = None
            if is_correct:
                correct_answers += 1
            else:
                mistake_tags.extend(question.tags)
                why_wrong = (
                    f"That answer is not correct for this question. The expected answer is "
                    f"'{question.correct_answer}'. {question.explanation}"
                )
            feedback.append(
                QuestionFeedback(
                    question_id=question.question_id,
                    prompt=question.prompt,
                    correct_answer=question.correct_answer,
                    submitted_answer=submitted_answer,
                    explanation=question.explanation,
                    why_wrong=why_wrong,
                    is_correct=is_correct,
                    tags=tuple(question.tags),
                )
            )

        total_questions = len(lesson.quiz_questions)
        score_percent = round((correct_answers / total_questions) * 100.0, 2) if total_questions else 0.0

        attempt = QuizAttempt(
            attempt_id=str(uuid4()),
            user_id=user_id,
            lesson_id=lesson.lesson_id,
            score_percent=score_percent,
            mistake_tags=list(dict.fromkeys(mistake_tags)),
        )
        self.quiz_attempt_repository.save(attempt)
        self.quiz_attempt_repository.save_question_results(
            attempt=attempt,
            topic_id=lesson.topic,
            results=tuple((question, item.is_correct) for question, item in zip(lesson.quiz_questions, feedback, strict=True)),
            track_outstanding=not practice_mode,
        )

        topic_summary = self.topic_attempt_summary(user_id, lesson.topic)
        if practice_mode:
            topic_summary = prior_topic_summary or TopicAttemptSummary(
                topic_id=lesson.topic,
                attempts=0,
                average_score=0.0,
                latest_score=None,
                page_passed=False,
                topic_passed=False,
            )

        if topic_summary is None:
            raise ValueError("Topic attempt summary was not available after saving an attempt.")

        pending_incorrect_count = 0
        progression_blocked = False
        if not practice_mode:
            pending_incorrect_count = len(
                self.quiz_attempt_repository.list_pending_incorrect_questions(
                    user_id,
                    topic_id=lesson.topic,
                )
            )
            progression_blocked = topic_summary.topic_passed and pending_incorrect_count > 0

        if not practice_mode:
            progress.record_quiz_attempt(score_percent)
            progress.current_level = max(progress.current_level, lesson.level)
            if topic_summary.topic_passed and not progression_blocked:
                progress.update_mastery(lesson.topic, topic_summary.average_score / 100.0)
                progress.current_level = min(len(self.content_library.all_topics()),
                                             max(progress.current_level, lesson.level + 1))
            else:
                progress.update_mastery(
                    lesson.topic,
                    min(topic_summary.average_score / 100.0, self.difficulty_manager.mastery_threshold - 0.01),
                )

            assessment = self.difficulty_manager.assess_user(progress)
            progress.current_difficulty = assessment.next_difficulty
            progress.current_cefr_band = self.content_library.target_cefr_band(progress.current_level)
            self._update_skill_scores(progress, lesson, score_percent)
            self.user_progress_repository.save(progress)
            if progression_blocked:
                action = "remediation"
            else:
                action = "advance" if topic_summary.topic_passed else ("hold" if topic_summary.page_passed else "review")
        else:
            action = "practice"

        return QuizResult(
            lesson=lesson,
            score_percent=score_percent,
            average_score_percent=topic_summary.average_score,
            correct_answers=correct_answers,
            total_questions=total_questions,
            action=action,
            next_topic=self._next_remediation_topic(user_id) or self.content_library.next_topic_for_user(progress),
            topic_attempts=topic_summary.attempts,
            topic_passed=topic_summary.topic_passed and not progression_blocked,
            pending_incorrect_count=pending_incorrect_count,
            feedback=tuple(feedback),
            updated_progress=progress,
        )

    def _attempts_for_topic(self, user_id: str, topic_id: str) -> list[QuizAttempt]:
        attempts = self.quiz_attempt_repository.list_for_user(user_id, limit=200)
        topic_attempts: list[QuizAttempt] = []
        for attempt in reversed(attempts):
            lesson = self.lesson_repository.get(attempt.lesson_id)
            if lesson is not None and lesson.topic == topic_id and not self._is_practice_lesson(lesson):
                topic_attempts.append(attempt)
        return topic_attempts

    def _next_remediation_topic(self, user_id: str) -> TopicMetadata | None:
        for topic in self.content_library.all_topics():
            pending_questions = self.quiz_attempt_repository.list_pending_incorrect_questions(
                user_id,
                topic_id=topic.topic_id,
            )
            if not pending_questions:
                continue
            summary = self.topic_attempt_summary(user_id, topic.topic_id)
            if summary is None or not summary.topic_passed:
                continue
            return topic
        return None

    def _maybe_start_remediation_session(self, user_id: str, topic_id: str) -> LessonSession | None:
        topic = self.content_library.get_topic(topic_id)
        if topic is None:
            raise ValueError(f"Unknown topic '{topic_id}'.")

        pending_questions = tuple(
            self.quiz_attempt_repository.list_pending_incorrect_questions(
                user_id,
                topic_id=topic_id,
            )
        )
        if not pending_questions:
            return None

        summary = self.topic_attempt_summary(user_id, topic_id)
        if summary is None or not summary.topic_passed:
            return None

        lesson = self._build_remediation_lesson(user_id, topic, pending_questions)
        self.lesson_repository.save(user_id, lesson)
        return LessonSession(
            page_kind="lesson",
            topic=topic,
            session_goal="remediation",
            resumed=False,
            source="system",
            lesson=lesson,
            warnings=(
                f"{len(pending_questions)} previously incorrect question(s) must be answered correctly before this level can advance.",
            ),
        )

    def _needs_intro(self, user_id: str, topic_id: str) -> bool:
        return not any(lesson.topic == topic_id for lesson in self.lesson_repository.list_for_user(user_id, limit=50))

    def _topic_focus_tags(self, user_id: str, topic_id: str) -> tuple[str, ...]:
        topic_attempts = self._attempts_for_topic(user_id, topic_id)
        if not topic_attempts:
            return ()
        latest = topic_attempts[-1]
        return tuple(dict.fromkeys(latest.mistake_tags[:3]))

    def _infer_session_goal(self, user_id: str, topic_id: str) -> str:
        summary = self.topic_attempt_summary(user_id, topic_id)
        if summary is None or summary.attempts == 0:
            return "lesson"
        if summary.topic_passed and self.quiz_attempt_repository.list_pending_incorrect_questions(user_id, topic_id=topic_id):
            return "remediation"
        return "lesson" if summary.topic_passed else "review"

    def _principles_for_topic(self, topic: TopicMetadata) -> tuple[str, ...]:
        focus = [self._humanize_focus_tag(tag) for tag in topic.grammar_focus[:4]]
        principles = [
            f"Level {topic.level} centres on {topic.description.rstrip('.')}.",
        ]
        if focus:
            principles.append(f"You will practise: {', '.join(focus)}.")
        principles.extend(LEVEL_PRINCIPLES.get(topic.topic_id, ()))
        if topic.prerequisites:
            prerequisite_titles = [
                self.content_library.get_topic(prerequisite_id).title
                for prerequisite_id in topic.prerequisites
                if self.content_library.get_topic(prerequisite_id) is not None
            ]
            if prerequisite_titles:
                principles.append(f"This builds on: {', '.join(prerequisite_titles)}.")
        principles.append(
            "You need at least five completed question sets for this level, with 80% or more on the current set and an 80% or higher average across all sets, before the app advances you."
        )
        return tuple(principles)

    def _humanize_focus_tag(self, tag: str) -> str:
        return tag.replace("_", " ")

    def _record_topic_vocabulary(self, user_id: str, topic_id: str) -> None:
        for word, definition in self.content_library.vocabulary_for_topic(topic_id):
            self._upsert_wordbank_entry(
                user_id=user_id,
                word=word,
                definition=definition,
                topic_id=topic_id,
            )

    def _extract_lesson_translations(self, lesson: Lesson) -> dict[str, str]:
        """Extract simple "X means Y" or "... meaning Y" glosses from lesson text and question explanations.

        Returns mapping of normalized Romanian text -> English gloss (raw string).
        """
        translations: dict[str, str] = {}
        pattern_means = re.compile(r"['\"](?P<r>[^'\"]+)['\"]\s+means\s+['\"](?P<e>[^'\"]+)['\"]", re.I)
        pattern_meaning = re.compile(r"['\"](?P<r>[^'\"]+)['\"][^\n]{0,120}?meaning\s+['\"](?P<e>[^'\"]+)['\"]", re.I)
        sources = [lesson.explanation_text or ""] + [q.explanation or "" for q in lesson.quiz_questions]
        for src in sources:
            if not src:
                continue
            for m in pattern_means.finditer(src):
                r = self._normalize_wordbank_text(m.group("r"))
                e = m.group("e").strip()
                if r:
                    translations.setdefault(r, e)
            for m in pattern_meaning.finditer(src):
                r = self._normalize_wordbank_text(m.group("r"))
                e = m.group("e").strip()
                if r:
                    translations.setdefault(r, e)
        return translations

    def _record_lesson_vocabulary(self, user_id: str, lesson: Lesson) -> None:
        # Pre-extract inline glosses from lesson explanations and question explanations
        translations = self._extract_lesson_translations(lesson)
        for sentence in lesson.example_sentences:
            # Use the example's English translation as the word definition so learners see the direct gloss.
            context_definition = sentence.english.strip()
            for token in self._extract_wordbank_tokens(sentence.romanian):
                # Prefer an extracted translation/gloss when available.
                normalized_token = self._normalize_wordbank_text(token)
                definition = translations.get(normalized_token)
                if not definition:
                    # Try simple stemming heuristics to find a lemma match (strip common definite/article endings)
                    for suffix in ("ul", "ului", "lor", "ii", "i", "a", "e", "le"):
                        if normalized_token.endswith(suffix) and len(normalized_token) > len(suffix) + 1:
                            stem = normalized_token[: -len(suffix)]
                            if stem in translations:
                                definition = translations[stem]
                                break
                self._upsert_wordbank_entry(
                    user_id=user_id,
                    word=token,
                    definition=definition or context_definition,
                    topic_id=lesson.topic,
                )
                # Attempt to add verb conjugation data for tokens that are verbs. This uses AI enrichment when available.
                try:
                    self._maybe_upsert_verbbank_entry(user_id=user_id, token=token, topic_id=lesson.topic)
                except Exception:
                    pass

    def _upsert_wordbank_entry(
            self,
            *,
            user_id: str,
            word: str,
            definition: str,
            topic_id: str,
    ) -> None:
        normalized_word = self._normalize_wordbank_text(word)
        normalized_definition = definition.strip()
        if not normalized_word or not normalized_definition:
            return
        self.wordbank_repository.upsert(
            WordbankEntry(
                user_id=user_id,
                word=normalized_word,
                definition=normalized_definition,
                topic=topic_id,
            )
        )

    def _extract_wordbank_tokens(self, text: str) -> tuple[str, ...]:
        seen: set[str] = set()
        tokens: list[str] = []
        if not text:
            return tuple()
        # Normalize Unicode forms (NFC) so combining marks and precomposed
        # characters match the token regex consistently.
        text = unicodedata.normalize("NFC", text)
        # Replace common typographic apostrophes and dashes with ASCII
        # equivalents so they are matched by the token pattern.
        text = text.replace("’", "'").replace("‘", "'").replace("–", "-").replace("—", "-")
        for match in WORD_TOKEN_PATTERN.finditer(text):
            token = self._normalize_wordbank_text(match.group(0))
            if not token or token in seen:
                continue
            seen.add(token)
            tokens.append(token)
        return tuple(tokens)

    def _normalize_wordbank_text(self, text: str) -> str:
        return " ".join(text.strip().split()).casefold()

    def _parse_verbbank_conjugations(self, conjugations: str) -> object:
        stripped = conjugations.strip()
        if not stripped:
            return {}
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return stripped

    def _normalize_person_label(self, label: str) -> str:
        normalized = label.strip().casefold().replace(" ", "")
        aliases = {
            "eu": "eu",
            "tu": "tu",
            "el": "el/ea",
            "ea": "el/ea",
            "el/ea": "el/ea",
            "noi": "noi",
            "voi": "voi",
            "ei": "ei/ele",
            "ele": "ei/ele",
            "ei/ele": "ei/ele",
        }
        return aliases.get(normalized, label.strip())

    def _normalize_verbbank_person_forms(self, value: object) -> dict[str, str]:
        if isinstance(value, Mapping):
            normalized: dict[str, str] = {}
            for raw_label, raw_form in value.items():
                if not isinstance(raw_label, str) or not isinstance(raw_form, str):
                    continue
                form = raw_form.strip()
                if not form:
                    continue
                normalized[self._normalize_person_label(raw_label)] = form
            return normalized
        if not isinstance(value, str):
            return {}

        normalized: dict[str, str] = {}
        for chunk in re.split(r"[;,]\s*", value.strip()):
            piece = chunk.strip()
            if not piece:
                continue
            match = re.match(r"^(eu|tu|el/ea|el|ea|noi|voi|ei/ele|ei|ele)\s+(.+)$", piece, flags=re.IGNORECASE)
            if match is None:
                continue
            normalized[self._normalize_person_label(match.group(1))] = match.group(2).strip()
        return normalized

    def _normalize_legacy_verbbank_string(self, value: str) -> dict[str, object]:
        text = value.strip().strip('"')
        if not text:
            return {}

        match = re.match(r"^(?P<infinitive>[^()]+?)\s*\((?P<body>.+)\)$", text)
        if match is None:
            return {"infinitive": text} if text.startswith("a ") else {}

        present: dict[str, str] = {}
        participle = ""
        gerund = ""
        for chunk in (part.strip() for part in match.group("body").split(",")):
            if not chunk:
                continue
            forms = self._normalize_verbbank_person_forms(chunk)
            if forms:
                present.update(forms)
                continue
            if not gerund and chunk.endswith("nd"):
                gerund = chunk
                continue
            if not participle:
                participle = chunk

        normalized: dict[str, object] = {"infinitive": match.group("infinitive").strip()}
        if present:
            normalized["present"] = present
        if participle:
            normalized["participle"] = participle
        if gerund:
            normalized["gerund"] = gerund
        return normalized

    def _normalize_verbbank_conjugations(self, value: object) -> dict[str, object]:
        if isinstance(value, str):
            return self._normalize_legacy_verbbank_string(value)
        if not isinstance(value, Mapping):
            return {}

        normalized: dict[str, object] = {}
        infinitive = str(value.get("infinitive", "")).strip() if value.get("infinitive") is not None else ""
        if not infinitive and value.get("lemma") is not None:
            infinitive = str(value.get("lemma")).strip()
        if infinitive:
            normalized["infinitive"] = infinitive

        for tense in ("present", "past", "future"):
            forms = self._normalize_verbbank_person_forms(value.get(tense))
            if forms:
                normalized[tense] = forms

        participle = ""
        if value.get("participle") is not None:
            participle = str(value.get("participle")).strip()
        if not participle and isinstance(value.get("past"), Mapping):
            raw_past = value.get("past")
            if raw_past.get("participle") is not None:
                participle = str(raw_past.get("participle")).strip()
        if participle:
            normalized["participle"] = participle

        gerund = ""
        if value.get("gerund") is not None:
            gerund = str(value.get("gerund")).strip()
        if not gerund and value.get("present_participle") is not None:
            gerund = str(value.get("present_participle")).strip()
        if gerund:
            normalized["gerund"] = gerund
        return normalized

    def _merge_verbbank_conjugations(
        self,
        existing: dict[str, object],
        fresh: dict[str, object],
    ) -> dict[str, object]:
        merged: dict[str, object] = {}
        for scalar_key in ("infinitive", "participle", "gerund"):
            scalar_value = str(fresh.get(scalar_key, "")).strip() or str(existing.get(scalar_key, "")).strip()
            if scalar_value:
                merged[scalar_key] = scalar_value

        for tense in ("present", "past", "future"):
            combined_forms: dict[str, str] = {}
            for source in (existing.get(tense), fresh.get(tense)):
                if not isinstance(source, Mapping):
                    continue
                for raw_label, raw_form in source.items():
                    if not isinstance(raw_label, str) or not isinstance(raw_form, str):
                        continue
                    form = raw_form.strip()
                    if form:
                        combined_forms[self._normalize_person_label(raw_label)] = form
            if combined_forms:
                merged[tense] = combined_forms
        return merged

    def _serialize_verbbank_conjugations(self, payload: dict[str, object], fallback: str) -> str:
        if payload:
            return json.dumps(payload, ensure_ascii=False)
        return fallback

    def _translation_is_usable(self, translation: str) -> bool:
        candidate = translation.strip()
        if not candidate:
            return False
        if candidate.casefold().startswith("seen in example:"):
            return False
        if candidate.endswith((".", "!", "?")):
            return False
        return len(candidate.split()) <= 6

    def _fallback_verbbank_translation(self, user_id: str, verb: str) -> str:
        matches = list(self.wordbank_repository.search_for_user(user_id, query=verb, limit=5))
        for entry in matches:
            if entry.word == verb and self._translation_is_usable(entry.definition):
                return entry.definition.strip()
        return ""

    def _verbbank_has_core_forms(self, payload: dict[str, object]) -> bool:
        if not str(payload.get("infinitive", "")).strip():
            return False
        present = payload.get("present")
        if not isinstance(present, Mapping) or not present.get("eu") or not present.get("el/ea"):
            return False

        has_past = bool(str(payload.get("participle", "")).strip())
        past = payload.get("past")
        if isinstance(past, Mapping) and (past.get("eu") or past.get("el/ea")):
            has_past = True

        future = payload.get("future")
        has_future = isinstance(future, Mapping) and bool(future.get("eu") or future.get("el/ea"))
        return has_past and has_future

    def _verbbank_needs_enrichment(self, entry: VerbbankEntry) -> bool:
        payload = self._normalize_verbbank_conjugations(self._parse_verbbank_conjugations(entry.conjugations))
        return not self._translation_is_usable(entry.translation) or not self._verbbank_has_core_forms(payload)

    def _refresh_verbbank_entries(self, user_id: str, entries: list[VerbbankEntry]) -> bool:
        if not entries or self.ai_service is None:
            return False

        candidates = [entry.verb for entry in entries if self._verbbank_needs_enrichment(entry)]
        if not candidates:
            return False

        conjugation_updates: dict[str, object] = {}
        if hasattr(self.ai_service, "generate_conjugations"):
            try:
                conjugation_updates = self.ai_service.generate_conjugations(candidates)
            except Exception:
                conjugation_updates = {}

        gloss_updates: dict[str, str] = {}
        if hasattr(self.ai_service, "generate_glosses"):
            try:
                gloss_updates = self.ai_service.generate_glosses(candidates)
            except Exception:
                gloss_updates = {}

        updated_any = False
        for entry in entries:
            if entry.verb not in candidates:
                continue
            existing_payload = self._normalize_verbbank_conjugations(self._parse_verbbank_conjugations(entry.conjugations))
            fresh_payload = self._normalize_verbbank_conjugations(conjugation_updates.get(entry.verb))
            merged_payload = self._merge_verbbank_conjugations(existing_payload, fresh_payload)
            translation = gloss_updates.get(entry.verb, "").strip()
            if not self._translation_is_usable(translation):
                translation = entry.translation.strip()
            if not self._translation_is_usable(translation):
                translation = self._fallback_verbbank_translation(user_id, entry.verb)

            serialized = self._serialize_verbbank_conjugations(merged_payload, entry.conjugations)
            if serialized == entry.conjugations and translation == entry.translation:
                continue

            self.verbbank_repository.upsert(
                VerbbankEntry(
                    user_id=entry.user_id,
                    verb=entry.verb,
                    conjugations=serialized,
                    translation=translation,
                    topic=entry.topic,
                    first_seen_at=entry.first_seen_at,
                )
            )
            updated_any = True
        return updated_any

    def _maybe_upsert_verbbank_entry(self, *, user_id: str, token: str, topic_id: str) -> None:
        """If the token appears to be a verb, ask AI for conjugations and persist a verbbank entry.
        This is best-effort: failures are ignored so learning flow is not disrupted.
        """
        normalized_token = self._normalize_wordbank_text(token)
        if not normalized_token:
            return
        existing_entry = None
        try:
            matches = list(self.verbbank_repository.search_for_user(user_id, query=normalized_token, limit=25))
            existing_entry = next((entry for entry in matches if entry.verb == normalized_token), None)
            if existing_entry is not None and not self._verbbank_needs_enrichment(existing_entry):
                return
        except Exception:
            existing_entry = None

        try:
            if not self.ai_service or not hasattr(self.ai_service, "generate_conjugations"):
                return
            conj_map = self.ai_service.generate_conjugations([normalized_token])
            conj = conj_map.get(normalized_token)
            normalized_conjugations = self._normalize_verbbank_conjugations(conj)
            serialized_conjugations = self._serialize_verbbank_conjugations(
                normalized_conjugations,
                json.dumps(conj, ensure_ascii=False) if conj else "",
            )
            if not serialized_conjugations:
                return

            translation = ""
            try:
                if hasattr(self.ai_service, "generate_glosses"):
                    glosses = self.ai_service.generate_glosses([normalized_token])
                    translation = glosses.get(normalized_token) or ""
                if not self._translation_is_usable(translation) and existing_entry is not None:
                    translation = existing_entry.translation
                if not self._translation_is_usable(translation):
                    translation = self._fallback_verbbank_translation(user_id, normalized_token)
            except Exception:
                translation = ""

            entry_kwargs = {
                "user_id": user_id,
                "verb": normalized_token,
                "conjugations": serialized_conjugations,
                "translation": translation,
                "topic": topic_id,
            }
            if existing_entry is not None:
                entry_kwargs["first_seen_at"] = existing_entry.first_seen_at

            self.verbbank_repository.upsert(VerbbankEntry(**entry_kwargs))
        except Exception:
            return

    def _clear_user_state(self, user_id: str) -> None:
        self.quiz_attempt_repository.delete_for_user(user_id)
        self.lesson_repository.delete_for_user(user_id)
        self.wordbank_repository.delete_for_user(user_id)
        try:
            self.verbbank_repository.delete_for_user(user_id)
        except Exception:
            pass
        self.user_progress_repository.delete(user_id)

    def _update_skill_scores(self, progress: UserProgress, lesson: Lesson, score_percent: float) -> None:
        skill_updates: dict[str, list[float]] = {"grammar": [score_percent]}
        integrated_types = {
            "sentence_transformation",
            "dialogue_completion",
            "guided_writing",
            "reading_comprehension",
        }
        for question in lesson.quiz_questions:
            question_type = question.question_type.value
            if question_type in integrated_types:
                skill_updates.setdefault("integrated_grammar", []).append(score_percent)
            if question_type == "dialogue_completion":
                skill_updates.setdefault("dialogue", []).append(score_percent)
            if question_type == "reading_comprehension":
                skill_updates.setdefault("reading", []).append(score_percent)
            if question_type == "guided_writing":
                skill_updates.setdefault("writing", []).append(score_percent)

        for skill_name, values in skill_updates.items():
            previous = progress.skill_scores.get(skill_name)
            incoming = sum(values) / len(values)
            blended = incoming if previous is None else round((previous + incoming) / 2.0, 2)
            progress.update_skill_score(skill_name, blended)

    def _roadmap_entries(
            self,
            progress: UserProgress,
            next_topic: TopicMetadata | None,
    ) -> tuple[RoadmapProgressEntry, ...]:
        entries: list[RoadmapProgressEntry] = []
        for topic in self.content_library.all_topics():
            mastery_percent = int(round(progress.mastery_matrix.get(topic.topic_id, 0.0) * 100))
            if mastery_percent >= int(self.difficulty_manager.mastery_threshold * 100):
                status = "mastered"
            elif next_topic is not None and next_topic.topic_id == topic.topic_id:
                status = "current"
            elif self.difficulty_manager.topic_is_allowed(progress, topic.topic_id):
                status = "available"
            else:
                status = "locked"
            entries.append(
                RoadmapProgressEntry(
                    level=topic.level,
                    topic_id=topic.topic_id,
                    title=topic.title,
                    cefr_band=topic.cefr_band.value,
                    mastery_percent=mastery_percent,
                    status=status,
                )
            )
        return tuple(entries)

    def _answers_match(self, expected: str, submitted: str) -> bool:
        return self._normalize_answer(expected) == self._normalize_answer(submitted)

    def _apply_recent_question_cooldown(
        self,
        *,
        topic_id: str,
        lesson: Lesson,
        session_goal: str,
        excluded_question_keys: set[tuple[str, str, str, str]],
    ) -> tuple[Lesson, tuple[str, ...]]:
        if not excluded_question_keys:
            return lesson, ()

        kept_questions: list[Question] = []
        blocked_indexes: list[int] = []
        used_keys: set[tuple[str, str, str, str]] = set()
        for index, question in enumerate(lesson.quiz_questions):
            key = self._question_cooldown_key(topic_id, question)
            if key in excluded_question_keys:
                blocked_indexes.append(index)
                continue
            kept_questions.append(question)
            used_keys.add(key)

        if not blocked_indexes:
            return lesson, ()

        replacement_count = len(blocked_indexes)
        replacement_lesson = self.content_library.build_fallback_lesson(
            topic_id,
            difficulty=lesson.difficulty,
            question_count=max(len(lesson.quiz_questions) * 3, replacement_count),
            session_goal=session_goal,
            excluded_question_keys=tuple(excluded_question_keys | used_keys),
        )

        replacements: list[Question] = []
        replacement_keys = set(excluded_question_keys) | used_keys
        for candidate in replacement_lesson.quiz_questions:
            key = self._question_cooldown_key(topic_id, candidate)
            if key in replacement_keys:
                continue
            replacements.append(candidate)
            replacement_keys.add(key)
            if len(replacements) >= replacement_count:
                break

        if len(replacements) < replacement_count:
            return lesson, (
                "Some recently answered-correct questions could not be replaced because too few alternative archived questions were available.",
            )

        updated_questions = list(lesson.quiz_questions)
        for index, replacement in zip(blocked_indexes, replacements, strict=True):
            updated_questions[index] = Question(
                question_id=updated_questions[index].question_id,
                prompt=replacement.prompt,
                question_type=replacement.question_type,
                difficulty_rating=replacement.difficulty_rating,
                cefr_band=replacement.cefr_band,
                correct_answer=replacement.correct_answer,
                explanation=replacement.explanation,
                tags=list(replacement.tags),
                options=list(replacement.options),
                hint=replacement.hint,
                rubric=dict(replacement.rubric),
            )

        refreshed_lesson = Lesson(
            lesson_id=lesson.lesson_id,
            topic=lesson.topic,
            level=lesson.level,
            cefr_band=lesson.cefr_band,
            difficulty=lesson.difficulty,
            explanation_text=lesson.explanation_text,
            example_sentences=list(lesson.example_sentences),
            key_rules=list(lesson.key_rules),
            quiz_questions=updated_questions,
            created_at=lesson.created_at,
        )
        return refreshed_lesson, ("Replaced recently answered-correct questions with different archived questions.",)

    def _build_remediation_lesson(
        self,
        user_id: str,
        topic: TopicMetadata,
        pending_questions: tuple[Question, ...],
    ) -> Lesson:
        progress = self.get_or_create_user_progress(user_id)
        base_lesson = self.content_library.build_fallback_lesson(
            topic.topic_id,
            difficulty=progress.current_difficulty,
            question_count=max(len(pending_questions), 1),
            session_goal="review",
        )
        remediation_questions = [
            Question(
                question_id=f"remediation-{topic.topic_id}-q{index}",
                prompt=question.prompt,
                question_type=question.question_type,
                difficulty_rating=question.difficulty_rating,
                cefr_band=question.cefr_band,
                correct_answer=question.correct_answer,
                explanation=question.explanation,
                tags=list(question.tags),
                options=list(question.options),
                hint=question.hint,
                rubric=dict(question.rubric),
            )
            for index, question in enumerate(pending_questions, start=1)
        ]
        return Lesson(
            lesson_id=f"remediation-{topic.topic_id}-{uuid4()}",
            topic=topic.topic_id,
            level=topic.level,
            cefr_band=topic.cefr_band,
            difficulty=progress.current_difficulty,
            explanation_text=(
                "You must clear previously missed questions before this level can advance. "
                + base_lesson.explanation_text
            ),
            example_sentences=list(base_lesson.example_sentences),
            key_rules=[
                "Every question in this set was answered incorrectly in an earlier non-practice attempt.",
                "The level only advances after each pending question has later been answered correctly.",
                *base_lesson.key_rules,
            ],
            quiz_questions=remediation_questions,
        )

    def _ensure_unique_questions_in_lesson(
        self,
        *,
        topic_id: str,
        lesson: Lesson,
        session_goal: str,
        excluded_question_keys: set[tuple[str, str, str, str]],
    ) -> tuple[Lesson, tuple[str, ...]]:
        target_count = len(lesson.quiz_questions)
        unique_questions: list[Question] = []
        used_keys: set[tuple[str, str, str, str]] = set()
        duplicate_count = 0

        for question in lesson.quiz_questions:
            key = self._question_cooldown_key(topic_id, question)
            if key in used_keys:
                duplicate_count += 1
                continue
            used_keys.add(key)
            unique_questions.append(question)

        if duplicate_count == 0:
            return lesson, ()

        replacement_lesson = self.content_library.build_fallback_lesson(
            topic_id,
            difficulty=lesson.difficulty,
            question_count=max(target_count * 3, duplicate_count),
            session_goal=session_goal,
            excluded_question_keys=tuple(excluded_question_keys | used_keys),
        )

        for candidate in replacement_lesson.quiz_questions:
            key = self._question_cooldown_key(topic_id, candidate)
            if key in used_keys:
                continue
            used_keys.add(key)
            unique_questions.append(candidate)
            if len(unique_questions) >= target_count:
                break

        refreshed_questions = [
            Question(
                question_id=f"{lesson.lesson_id}-q{index}",
                prompt=question.prompt,
                question_type=question.question_type,
                difficulty_rating=question.difficulty_rating,
                cefr_band=question.cefr_band,
                correct_answer=question.correct_answer,
                explanation=question.explanation,
                tags=list(question.tags),
                options=list(question.options),
                hint=question.hint,
                rubric=dict(question.rubric),
            )
            for index, question in enumerate(unique_questions[:target_count], start=1)
        ]
        refreshed_lesson = Lesson(
            lesson_id=lesson.lesson_id,
            topic=lesson.topic,
            level=lesson.level,
            cefr_band=lesson.cefr_band,
            difficulty=lesson.difficulty,
            explanation_text=lesson.explanation_text,
            example_sentences=list(lesson.example_sentences),
            key_rules=list(lesson.key_rules),
            quiz_questions=refreshed_questions,
            created_at=lesson.created_at,
        )

        if len(refreshed_questions) < target_count:
            return refreshed_lesson, (
                "Removed duplicate questions from the lesson, but too few unique replacements were available to restore the full set.",
            )
        return refreshed_lesson, ("Removed duplicate questions from the lesson and replaced them with unique alternatives.",)

    def _question_cooldown_key(self, topic_id: str, question: Question) -> tuple[str, str, str, str]:
        return (
            topic_id,
            question.question_type.value,
            question.prompt.strip().casefold(),
            question.correct_answer.strip().casefold(),
        )

    def _ensure_english_guidance_lesson(
        self,
        *,
        topic_id: str,
        lesson: Lesson,
        session_goal: str,
        excluded_question_keys: set[tuple[str, str, str, str]],
    ) -> tuple[Lesson, tuple[str, ...]]:
        if not self._lesson_has_non_english_guidance(lesson):
            return lesson, ()

        replacement_lesson = self.content_library.build_fallback_lesson(
            topic_id,
            difficulty=lesson.difficulty,
            question_count=len(lesson.quiz_questions),
            session_goal=session_goal,
            include_archived_questions=False,
            excluded_question_keys=tuple(excluded_question_keys),
        )
        return replacement_lesson, (
            "Replaced lesson content because some learner-facing guidance was in Romanian instead of English.",
        )

    def _lesson_has_non_english_guidance(self, lesson: Lesson) -> bool:
        if not hasattr(self.ai_service, "content_validator"):
            return False
        return bool(self.ai_service.content_validator.english_guidance_issues(lesson))

    def _normalize_answer(self, value: str) -> str:
        normalized = re.sub(r"\s+", " ", value.strip()).casefold()
        return normalized.rstrip(" .!?")

    def _is_practice_lesson(self, lesson: Lesson) -> bool:
        return lesson.lesson_id.startswith("practice-") or "-practice-" in lesson.lesson_id

    def _lesson_is_resume_ready(self, lesson: Lesson) -> bool:
        return all(not self._prompt_has_missing_context(question.prompt) for question in lesson.quiz_questions)

    def _prompt_has_missing_context(self, prompt: str) -> bool:
        lowered = prompt.casefold()
        references_dialogue = any(marker in lowered for marker in ("dialogue", "reply", "response", "conversation"))
        has_quotes = prompt.count("'") >= 2 or prompt.count('"') >= 2
        has_turn_markers = prompt.count(":") >= 2 and "___" in prompt
        if references_dialogue:
            return not (has_quotes or has_turn_markers)

        references_sentence = "sentence" in lowered and any(
            marker in lowered for marker in ("complete the sentence", "rewrite the sentence", "transform the sentence")
        )
        if references_sentence:
            has_sentence_pattern = "___" in prompt and prompt.count(":") >= 1 and len(prompt.split()) >= 8
            return not (has_quotes or has_sentence_pattern)

        return False
