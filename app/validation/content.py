from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from app.models import CEFRBand, ExampleSentence, Lesson, Question, QuestionType, TopicMetadata


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    path: str
    message: str


class ContentValidationError(Exception):
    def __init__(self, issues: tuple[ValidationIssue, ...]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues[:5]) or "unknown validation error"
        super().__init__(f"Generated content failed validation: {summary}")


def lesson_to_payload(lesson: Lesson) -> dict[str, Any]:
    return {
        "lesson_id": lesson.lesson_id,
        "topic": lesson.topic,
        "level": lesson.level,
        "cefr_band": lesson.cefr_band.value,
        "difficulty": lesson.difficulty,
        "explanation_text": lesson.explanation_text,
        "example_sentences": [
            {"romanian": sentence.romanian, "english": sentence.english}
            for sentence in lesson.example_sentences
        ],
        "key_rules": list(lesson.key_rules),
        "quiz_questions": [
            {
                "question_id": question.question_id,
                "type": question.question_type.value,
                "prompt": question.prompt,
                "options": list(question.options),
                "correct_answer": question.correct_answer,
                "explanation": question.explanation,
                "difficulty": question.difficulty_rating,
                "tags": list(question.tags),
                "hint": question.hint,
                "rubric": dict(question.rubric),
                "cefr_band": question.cefr_band.value,
            }
            for question in lesson.quiz_questions
        ],
    }


@dataclass(slots=True)
class ContentValidator:
    banned_terms: ClassVar[tuple[str, ...]] = (
        "dragon",
        "zombie",
        "alien invasion",
        "spaceship",
        "time machine",
        "teleport",
        "quantum reactor",
    )
    open_response_types: ClassVar[tuple[QuestionType, ...]] = (
        QuestionType.ENGLISH_TO_ROMANIAN,
        QuestionType.ROMANIAN_TO_ENGLISH,
        QuestionType.FILL_IN_THE_BLANK,
        QuestionType.SENTENCE_TRANSFORMATION,
        QuestionType.GUIDED_WRITING,
        QuestionType.READING_COMPREHENSION,
        QuestionType.DIALOGUE_COMPLETION,
    )
    english_signal_words: ClassVar[frozenset[str]] = frozenset(
        {
            "a",
            "an",
            "answer",
            "article",
            "articles",
            "because",
            "book",
            "choose",
            "complete",
            "correct",
            "dialogue",
            "english",
            "example",
            "examples",
            "explanation",
            "fill",
            "form",
            "forms",
            "give",
            "grammar",
            "guide",
            "hint",
            "in",
            "into",
            "lesson",
            "match",
            "noun",
            "nouns",
            "please",
            "prompt",
            "question",
            "read",
            "reply",
            "response",
            "rewrite",
            "rule",
            "rules",
            "sentence",
            "sentences",
            "singular",
            "some",
            "subject",
            "table",
            "the",
            "these",
            "this",
            "to",
            "translate",
            "use",
            "verb",
            "what",
            "while",
            "write",
            "you",
            "your",
        }
    )
    romanian_signal_words: ClassVar[frozenset[str]] = frozenset(
        {
            "alege",
            "acesta",
            "acestea",
            "acestui",
            "acum",
            "acordul",
            "articol",
            "articole",
            "articolele",
            "articolul",
            "atasat",
            "ataseaza",
            "baiat",
            "baiatul",
            "cartea",
            "cinema",
            "copii",
            "copiii",
            "copil",
            "copiii",
            "cu",
            "dai",
            "definita",
            "definite",
            "definit",
            "deoarece",
            "determin",
            "determinat",
            "desi",
            "corecta",
            "completeaza",
            "este",
            "exemplu",
            "exemple",
            "fata",
            "fetele",
            "film",
            "forma",
            "foloseste",
            "fratele",
            "gandeste",
            "gen",
            "gindeste",
            "hotarat",
            "hotarate",
            "hotarit",
            "indica",
            "insotite",
            "iar",
            "interesant",
            "limba",
            "masa",
            "masculin",
            "mi",
            "ni",
            "niste",
            "nehotarat",
            "numar",
            "parc",
            "pe",
            "propozitia",
            "reguli",
            "romana",
            "romane",
            "sau",
            "scaunele",
            "se",
            "sfarsit",
            "singular",
            "specific",
            "stau",
            "substantiv",
            "substantive",
            "substantivele",
            "substantivul",
            "sint",
            "sunt",
            "te",
            "textul",
            "transforma",
            "un",
            "unei",
            "urma",
            "va",
        }
    )
    _word_pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"[A-Za-z\u0102\u0103\u00C2\u00E2\u00CE\u00EE\u0218\u0219\u021A\u021B\u015E\u015F\u0162\u0163]+"
    )
    _romanian_characters: ClassVar[frozenset[str]] = frozenset(
        "\u0103\u00E2\u00EE\u0219\u021B\u015F\u0163\u0102\u00C2\u00CE\u0218\u021A\u015E\u0162"
    )
    _romanian_translation_table: ClassVar[dict[int, str]] = str.maketrans(
        {
            "\u0103": "a",
            "\u00E2": "a",
            "\u00EE": "i",
            "\u0219": "s",
            "\u021B": "t",
            "\u015F": "s",
            "\u0163": "t",
            "\u0102": "a",
            "\u00C2": "a",
            "\u00CE": "i",
            "\u0218": "s",
            "\u021A": "t",
            "\u015E": "s",
            "\u0162": "t",
        }
    )

    def validate_lesson_payload(
        self,
        payload: dict[str, Any],
        *,
        topic: TopicMetadata,
        expected_question_count: int,
    ) -> Lesson:
        issues: list[ValidationIssue] = []
        if not isinstance(payload, dict):
            raise ContentValidationError((ValidationIssue(path="$", message="Lesson payload must be a JSON object."),))

        self._validate_top_level(payload, topic, expected_question_count, issues)
        if issues:
            raise ContentValidationError(tuple(issues))

        lesson = self._build_lesson(payload, issues)
        self._validate_scope_and_sensibility(lesson, topic, issues)
        if issues:
            raise ContentValidationError(tuple(issues))
        return lesson

    def english_guidance_issues(self, lesson: Lesson) -> tuple[ValidationIssue, ...]:
        issues: list[ValidationIssue] = []
        self._validate_learner_guidance_language(lesson, issues)
        return tuple(issues)

    def _validate_top_level(
        self,
        payload: dict[str, Any],
        topic: TopicMetadata,
        expected_question_count: int,
        issues: list[ValidationIssue],
    ) -> None:
        required = (
            "lesson_id",
            "topic",
            "level",
            "cefr_band",
            "difficulty",
            "explanation_text",
            "example_sentences",
            "key_rules",
            "quiz_questions",
        )
        for key in required:
            if key not in payload:
                issues.append(ValidationIssue(path=key, message="Missing required field."))

        if issues:
            return

        self._require_non_empty_string(payload["lesson_id"], "lesson_id", issues)
        self._require_non_empty_string(payload["topic"], "topic", issues)
        self._require_int_in_range(payload["level"], "level", minimum=1, maximum=100, issues=issues)
        self._require_known_cefr(payload["cefr_band"], "cefr_band", issues)
        self._require_int_in_range(payload["difficulty"], "difficulty", minimum=1, maximum=10, issues=issues)
        self._require_non_empty_string(payload["explanation_text"], "explanation_text", issues)
        self._require_string_list(payload["key_rules"], "key_rules", minimum_length=1, issues=issues)
        self._require_list(payload["example_sentences"], "example_sentences", minimum_length=1, issues=issues)
        self._require_list(payload["quiz_questions"], "quiz_questions", minimum_length=1, issues=issues)

        if payload["topic"] != topic.topic_id:
            issues.append(ValidationIssue(path="topic", message=f"Expected topic '{topic.topic_id}'."))  # noqa: B950
        if payload["level"] != topic.level:
            issues.append(ValidationIssue(path="level", message=f"Expected level {topic.level}."))
        if payload["cefr_band"] != topic.cefr_band.value:
            issues.append(ValidationIssue(path="cefr_band", message=f"Expected CEFR band {topic.cefr_band.value}."))

        quiz_questions = payload.get("quiz_questions")
        if isinstance(quiz_questions, list) and len(quiz_questions) != expected_question_count:
            issues.append(
                ValidationIssue(
                    path="quiz_questions",
                    message=f"Expected exactly {expected_question_count} questions.",
                )
            )

    def _build_lesson(self, payload: dict[str, Any], issues: list[ValidationIssue]) -> Lesson:
        examples: list[ExampleSentence] = []
        for index, raw_example in enumerate(payload["example_sentences"]):
            path = f"example_sentences[{index}]"
            if not isinstance(raw_example, dict):
                issues.append(ValidationIssue(path=path, message="Example sentence must be an object."))
                continue
            romanian = raw_example.get("romanian")
            english = raw_example.get("english")
            self._require_non_empty_string(romanian, f"{path}.romanian", issues)
            self._require_non_empty_string(english, f"{path}.english", issues)
            if isinstance(romanian, str) and isinstance(english, str) and romanian.strip() and english.strip():
                examples.append(ExampleSentence(romanian=romanian.strip(), english=english.strip()))

        questions: list[Question] = []
        for index, raw_question in enumerate(payload["quiz_questions"]):
            path = f"quiz_questions[{index}]"
            if not isinstance(raw_question, dict):
                issues.append(ValidationIssue(path=path, message="Question must be an object."))
                continue
            question = self._build_question(raw_question, path, issues)
            if question is not None:
                questions.append(question)

        if issues:
            raise ContentValidationError(tuple(issues))

        try:
            return Lesson(
                lesson_id=payload["lesson_id"].strip(),
                topic=payload["topic"].strip(),
                level=payload["level"],
                cefr_band=CEFRBand(payload["cefr_band"]),
                difficulty=payload["difficulty"],
                explanation_text=payload["explanation_text"].strip(),
                example_sentences=examples,
                key_rules=[rule.strip() for rule in payload["key_rules"]],
                quiz_questions=questions,
            )
        except (TypeError, ValueError) as exc:
            raise ContentValidationError((ValidationIssue(path="$", message=str(exc)),)) from exc

    def _build_question(
        self,
        payload: dict[str, Any],
        path: str,
        issues: list[ValidationIssue],
    ) -> Question | None:
        start_issue_count = len(issues)
        required = (
            "question_id",
            "type",
            "prompt",
            "options",
            "correct_answer",
            "explanation",
            "difficulty",
            "tags",
            "hint",
            "rubric",
            "cefr_band",
        )
        for key in required:
            if key not in payload:
                issues.append(ValidationIssue(path=f"{path}.{key}", message="Missing required field."))
        if any(key not in payload for key in required):
            return None

        self._require_non_empty_string(payload["question_id"], f"{path}.question_id", issues)
        self._require_non_empty_string(payload["type"], f"{path}.type", issues)
        self._require_non_empty_string(payload["prompt"], f"{path}.prompt", issues)
        self._require_non_empty_string(payload["correct_answer"], f"{path}.correct_answer", issues)
        self._require_non_empty_string(payload["explanation"], f"{path}.explanation", issues)
        self._require_int_in_range(payload["difficulty"], f"{path}.difficulty", minimum=1, maximum=10, issues=issues)
        self._require_known_cefr(payload["cefr_band"], f"{path}.cefr_band", issues)
        self._require_list(payload["tags"], f"{path}.tags", minimum_length=1, issues=issues)

        question_type = payload["type"]
        options = payload["options"]
        hint = payload["hint"]
        rubric = payload["rubric"]

        if not isinstance(options, list):
            issues.append(ValidationIssue(path=f"{path}.options", message="Options must be a list."))
        elif any(not isinstance(option, str) or not option.strip() for option in options):
            issues.append(ValidationIssue(path=f"{path}.options", message="Options must contain non-empty strings."))
        elif len({option.strip().casefold() for option in options}) != len(options):
            issues.append(ValidationIssue(path=f"{path}.options", message="Options must be unique."))

        if not isinstance(payload["tags"], list) or any(not isinstance(tag, str) or not tag.strip() for tag in payload["tags"]):
            issues.append(ValidationIssue(path=f"{path}.tags", message="Tags must contain non-empty strings."))

        if hint is not None and (not isinstance(hint, str) or not hint.strip()):
            issues.append(ValidationIssue(path=f"{path}.hint", message="Hint must be null or a non-empty string."))

        if not isinstance(rubric, dict):
            issues.append(ValidationIssue(path=f"{path}.rubric", message="Rubric must be an object."))

        try:
            parsed_question_type = QuestionType(question_type)
        except ValueError:
            issues.append(ValidationIssue(path=f"{path}.type", message="Unsupported question type."))
            return None

        if len(issues) > start_issue_count:
            return None

        normalized_options = [option.strip() for option in options]
        normalized_answer = payload["correct_answer"].strip()
        if parsed_question_type == QuestionType.MULTIPLE_CHOICE:
            if len(normalized_options) < 2:
                issues.append(ValidationIssue(path=f"{path}.options", message="Multiple choice questions need at least two options."))
            if normalized_answer not in normalized_options:
                issues.append(ValidationIssue(path=f"{path}.correct_answer", message="Correct answer must appear in options."))
        elif parsed_question_type == QuestionType.ERROR_IDENTIFICATION:
            if len(normalized_options) < 2:
                issues.append(ValidationIssue(path=f"{path}.options", message="Error identification questions need at least two options."))
            if normalized_answer not in normalized_options:
                issues.append(ValidationIssue(path=f"{path}.correct_answer", message="Correct answer must appear in options."))
        elif parsed_question_type in self.open_response_types and len(normalized_answer) < 2:
            issues.append(ValidationIssue(path=f"{path}.correct_answer", message="Open-response style questions need a usable reference answer."))
        elif normalized_options and normalized_answer not in normalized_options:
            issues.append(ValidationIssue(path=f"{path}.correct_answer", message="Correct answer must match one of the provided options."))

        if parsed_question_type == QuestionType.GUIDED_WRITING and not rubric:
            issues.append(ValidationIssue(path=f"{path}.rubric", message="Guided writing questions require a rubric."))

        if len(issues) > start_issue_count:
            return None

        try:
            return Question(
                question_id=payload["question_id"].strip(),
                prompt=payload["prompt"].strip(),
                question_type=parsed_question_type,
                difficulty_rating=payload["difficulty"],
                cefr_band=CEFRBand(payload["cefr_band"]),
                correct_answer=normalized_answer,
                explanation=payload["explanation"].strip(),
                tags=[tag.strip() for tag in payload["tags"]],
                options=normalized_options,
                hint=hint.strip() if isinstance(hint, str) else None,
                rubric={str(key): str(value) for key, value in rubric.items()},
            )
        except (TypeError, ValueError) as exc:
            issues.append(ValidationIssue(path=path, message=str(exc)))
            return None

    def _validate_scope_and_sensibility(
        self,
        lesson: Lesson,
        topic: TopicMetadata,
        issues: list[ValidationIssue],
    ) -> None:
        allowed_tags = set(topic.grammar_focus) | {topic.topic_id}
        known_topic_ids = {
            "romanian_basics",
            "nouns_and_articles",
            "core_cases",
            "present_tense_verbs",
            "pronouns_and_tenses",
            "connected_communication",
            "narrative_b1_grammar",
            "b1_b2_transition",
            "b2_core_structures",
            "b2_consolidation",
        }

        self._check_text("explanation_text", lesson.explanation_text, issues, max_length=800)
        self._validate_learner_guidance_language(lesson, issues)
        seen_prompts: set[str] = set()
        integrated_count = 0
        guided_writing_count = 0
        reading_count = 0
        for index, sentence in enumerate(lesson.example_sentences):
            self._check_text(f"example_sentences[{index}].romanian", sentence.romanian, issues, max_length=180)
            self._check_text(f"example_sentences[{index}].english", sentence.english, issues, max_length=180)
            if topic.cefr_band in {CEFRBand.B1, CEFRBand.B2} and not self._looks_connected_context(sentence.romanian):
                issues.append(
                    ValidationIssue(
                        path=f"example_sentences[{index}].romanian",
                        message="B1-B2 lessons need at least one multi-clause or multi-sentence example.",
                    )
                )

        for index, question in enumerate(lesson.quiz_questions):
            prompt_key = question.prompt.casefold()
            if prompt_key in seen_prompts:
                issues.append(ValidationIssue(path=f"quiz_questions[{index}].prompt", message="Duplicate question prompt."))  # noqa: B950
            seen_prompts.add(prompt_key)
            self._check_text(f"quiz_questions[{index}].prompt", question.prompt, issues, max_length=320)
            self._check_text(f"quiz_questions[{index}].explanation", question.explanation, issues, max_length=500)
            if self._references_dialogue(question.prompt) and not self._has_dialogue_context(question.prompt):
                issues.append(
                    ValidationIssue(
                        path=f"quiz_questions[{index}].prompt",
                        message="Prompt references dialogue or a reply but does not include the actual dialogue context.",
                    )
                )
            if self._references_sentence_context(question.prompt) and not self._has_sentence_context(question.prompt):
                issues.append(
                    ValidationIssue(
                        path=f"quiz_questions[{index}].prompt",
                        message="Prompt references a sentence but does not include the actual sentence context.",
                    )
                )
            if question.question_type in {QuestionType.SENTENCE_TRANSFORMATION, QuestionType.DIALOGUE_COMPLETION}:
                if len(question.prompt.split()) < 6:
                    issues.append(
                        ValidationIssue(
                            path=f"quiz_questions[{index}].prompt",
                            message="Transformation and dialogue tasks need enough context to be assessable.",
                        )
                    )
            if topic.cefr_band in {CEFRBand.B1, CEFRBand.B2} and question.question_type in {
                QuestionType.SENTENCE_TRANSFORMATION,
                QuestionType.DIALOGUE_COMPLETION,
                QuestionType.READING_COMPREHENSION,
                QuestionType.GUIDED_WRITING,
            }:
                integrated_count += 1
                if len(question.prompt.split()) < 8:
                    issues.append(
                        ValidationIssue(
                            path=f"quiz_questions[{index}].prompt",
                            message="B1-B2 integrated tasks need a fuller prompt context.",
                        )
                    )
            if question.question_type == QuestionType.GUIDED_WRITING:
                guided_writing_count += 1
                if len(question.rubric) < 2:
                    issues.append(
                        ValidationIssue(
                            path=f"quiz_questions[{index}].rubric",
                            message="Guided writing tasks need at least two rubric criteria.",
                        )
                    )
            if question.question_type == QuestionType.READING_COMPREHENSION:
                reading_count += 1
                if len(question.prompt.split()) < 16:
                    issues.append(
                        ValidationIssue(
                            path=f"quiz_questions[{index}].prompt",
                            message="Reading comprehension tasks need a passage-length prompt.",
                        )
                    )

            if not (set(question.tags) & allowed_tags):
                issues.append(
                    ValidationIssue(
                        path=f"quiz_questions[{index}].tags",
                        message="Question tags do not match the requested lesson scope.",
                    )
                )
            off_scope_topics = [tag for tag in question.tags if tag in known_topic_ids and tag != topic.topic_id]
            if off_scope_topics:
                issues.append(
                    ValidationIssue(
                        path=f"quiz_questions[{index}].tags",
                        message=f"Question introduces off-scope topics: {', '.join(off_scope_topics)}.",
                    )
                )

            if question.cefr_band != topic.cefr_band:
                issues.append(
                    ValidationIssue(
                        path=f"quiz_questions[{index}].cefr_band",
                        message=f"Expected CEFR band {topic.cefr_band.value}.",
                    )
                )
        if topic.cefr_band == CEFRBand.B1 and integrated_count < 1:
            issues.append(ValidationIssue(path="quiz_questions", message="B1 lessons need at least one integrated task type."))
        if topic.cefr_band == CEFRBand.B2:
            if integrated_count < 2:
                issues.append(ValidationIssue(path="quiz_questions", message="B2 lessons need multiple integrated task types."))
            if guided_writing_count < 1:
                issues.append(ValidationIssue(path="quiz_questions", message="B2 lessons need at least one guided writing task."))
            if reading_count < 1:
                issues.append(ValidationIssue(path="quiz_questions", message="B2 lessons need at least one reading comprehension task."))

    def _validate_learner_guidance_language(
        self,
        lesson: Lesson,
        issues: list[ValidationIssue],
    ) -> None:
        self._check_expected_english("explanation_text", lesson.explanation_text, issues)
        for index, sentence in enumerate(lesson.example_sentences):
            self._check_expected_english(f"example_sentences[{index}].english", sentence.english, issues)
        for index, rule in enumerate(lesson.key_rules):
            self._check_expected_english(f"key_rules[{index}]", rule, issues)
        for index, question in enumerate(lesson.quiz_questions):
            self._check_expected_english(f"quiz_questions[{index}].prompt", question.prompt, issues)
            self._check_expected_english(f"quiz_questions[{index}].explanation", question.explanation, issues)
            if question.hint:
                self._check_expected_english(f"quiz_questions[{index}].hint", question.hint, issues)

    def _check_expected_english(
        self,
        path: str,
        value: str,
        issues: list[ValidationIssue],
    ) -> None:
        if self._looks_predominantly_romanian(value):
            issues.append(
                ValidationIssue(
                    path=path,
                    message="Learner-facing guidance must be written in English, not Romanian.",
                )
            )

    def _looks_predominantly_romanian(self, value: str) -> bool:
        lowered = value.strip().casefold()
        if len(lowered) < 5:
            return False

        romanian_score = 0
        if any(character in self._romanian_characters for character in lowered):
            romanian_score += 2

        normalized = lowered.translate(self._romanian_translation_table)
        tokens = self._word_pattern.findall(normalized)
        if not tokens:
            return False

        english_score = sum(token in self.english_signal_words for token in tokens)
        romanian_score += sum(token in self.romanian_signal_words for token in tokens)

        if romanian_score >= 4 and english_score == 0:
            return True
        return romanian_score >= english_score + 3

    def _check_text(
        self,
        path: str,
        value: str,
        issues: list[ValidationIssue],
        *,
        max_length: int,
    ) -> None:
        stripped = value.strip()
        if len(stripped) < 5:
            issues.append(ValidationIssue(path=path, message="Text is too short to be useful."))
        if len(stripped) > max_length:
            issues.append(ValidationIssue(path=path, message=f"Text exceeds maximum length of {max_length} characters."))  # noqa: B950
        lowered = stripped.casefold()
        for banned_term in self.banned_terms:
            if banned_term in lowered:
                issues.append(ValidationIssue(path=path, message=f"Text contains banned or nonsensical term '{banned_term}'."))  # noqa: B950

    def _looks_connected_context(self, value: str) -> bool:
        stripped = value.strip()
        if "." in stripped or "?" in stripped or "!" in stripped:
            return True
        connectors = (" cind ", " deoarece ", " pentru ca ", " dar ", " desi ", " ca sa ", " in timp ce ")
        lowered = f" {stripped.casefold()} "
        return any(connector in lowered for connector in connectors)

    def _references_dialogue(self, prompt: str) -> bool:
        lowered = prompt.casefold()
        return any(marker in lowered for marker in ("dialogue", "reply", "response", "conversation"))

    def _has_dialogue_context(self, prompt: str) -> bool:
        single_quotes = prompt.count("'")
        double_quotes = prompt.count('"')
        if single_quotes >= 2 or double_quotes >= 2:
            return True
        # Allow simple speaker-turn formatting like "A: ... B: ..."
        return prompt.count(":") >= 2 and "___" in prompt

    def _references_sentence_context(self, prompt: str) -> bool:
        lowered = prompt.casefold()
        return "sentence" in lowered and any(
            marker in lowered for marker in ("complete the sentence", "rewrite the sentence", "transform the sentence")
        )

    def _has_sentence_context(self, prompt: str) -> bool:
        single_quotes = prompt.count("'")
        double_quotes = prompt.count('"')
        if single_quotes >= 2 or double_quotes >= 2:
            return True
        # Allow direct blanked sentence patterns without quote marks.
        return "___" in prompt and prompt.count(":") >= 1 and len(prompt.split()) >= 8

    def _require_non_empty_string(self, value: Any, path: str, issues: list[ValidationIssue]) -> None:
        if not isinstance(value, str) or not value.strip():
            issues.append(ValidationIssue(path=path, message="Expected a non-empty string."))

    def _require_list(
        self,
        value: Any,
        path: str,
        minimum_length: int,
        issues: list[ValidationIssue],
    ) -> None:
        if not isinstance(value, list):
            issues.append(ValidationIssue(path=path, message="Expected a list."))
        elif len(value) < minimum_length:
            issues.append(ValidationIssue(path=path, message=f"Expected at least {minimum_length} items."))

    def _require_string_list(
        self,
        value: Any,
        path: str,
        minimum_length: int,
        issues: list[ValidationIssue],
    ) -> None:
        self._require_list(value, path, minimum_length, issues)
        if isinstance(value, list) and any(not isinstance(item, str) or not item.strip() for item in value):
            issues.append(ValidationIssue(path=path, message="Expected only non-empty strings."))

    def _require_int_in_range(
        self,
        value: Any,
        path: str,
        *,
        minimum: int,
        maximum: int,
        issues: list[ValidationIssue],
    ) -> None:
        if not isinstance(value, int):
            issues.append(ValidationIssue(path=path, message="Expected an integer."))
        elif not minimum <= value <= maximum:
            issues.append(ValidationIssue(path=path, message=f"Expected a value between {minimum} and {maximum}."))

    def _require_known_cefr(self, value: Any, path: str, issues: list[ValidationIssue]) -> None:
        if not isinstance(value, str):
            issues.append(ValidationIssue(path=path, message="Expected a CEFR band string."))
            return
        try:
            CEFRBand(value)
        except ValueError:
            issues.append(ValidationIssue(path=path, message="Unknown CEFR band."))
