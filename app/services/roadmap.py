from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.models import (
    PLACEMENT_TEST_BLUEPRINT,
    CEFRBand,
    ExampleSentence,
    Lesson,
    PlacementTestSection,
    Question,
    QuestionType,
    ROADMAP_TOPICS,
    TopicMetadata,
    UserProgress,
)


@dataclass(frozen=True, slots=True)
class FallbackQuestionTemplate:
    prompt: str
    question_type: QuestionType
    correct_answer: str
    explanation: str
    tags: tuple[str, ...]
    options: tuple[str, ...] = ()
    hint: str | None = None
    rubric: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class FallbackLessonTemplate:
    explanation_text: str
    key_rules: tuple[str, ...]
    example_sentences: tuple[ExampleSentence, ...]
    questions: tuple[FallbackQuestionTemplate, ...]


FALLBACK_LESSON_TEMPLATES: dict[str, FallbackLessonTemplate] = {
    "romanian_basics": FallbackLessonTemplate(
        explanation_text="Romanian basics start with diacritics, simple greetings, and the present tense of 'a fi'.",
        key_rules=(
            "Romanian uses the diacritics a, a with breve, a with circumflex, i with circumflex, s with comma, and t with comma.",
            "The verb 'a fi' means 'to be' and appears in short daily phrases such as 'Eu sunt' and 'Noi suntem'.",
        ),
        example_sentences=(
            ExampleSentence(romanian="Eu sunt aici.", english="I am here."),
            ExampleSentence(romanian="Buna, eu sunt Ana.", english="Hello, I am Ana."),
        ),
        questions=(
            FallbackQuestionTemplate(
                prompt="Choose the correct Romanian form of 'I am'.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("este", "sunt", "suntem", "esti"),
                correct_answer="sunt",
                explanation="'Eu sunt' means 'I am'.",
                tags=("romanian_basics", "a_fi_present"),
                hint="Match the form used with 'eu'.",
            ),
            FallbackQuestionTemplate(
                prompt="Fill in the blank: Buna, eu ___ Maria.",
                question_type=QuestionType.FILL_IN_THE_BLANK,
                correct_answer="sunt",
                explanation="The sentence needs the first-person singular form of 'a fi'.",
                tags=("romanian_basics", "a_fi_present"),
                hint="Use the form that means 'am'.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into Romanian: Hello.",
                question_type=QuestionType.ENGLISH_TO_ROMANIAN,
                correct_answer="Buna",
                explanation="'Buna' is a standard beginner greeting.",
                tags=("romanian_basics", "greetings"),
                hint="Use the common informal greeting.",
            ),
            FallbackQuestionTemplate(
                prompt="Which word contains the Romanian letter with breve?",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("fata", "fara", "fată", "fi"),
                correct_answer="fată",
                explanation="The letter a with breve is a Romanian diacritic.",
                tags=("romanian_basics", "diacritics"),
                hint="Look for the special mark above the a.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into English: Eu sunt student.",
                question_type=QuestionType.ROMANIAN_TO_ENGLISH,
                correct_answer="I am a student.",
                explanation="'Eu sunt student' translates directly to 'I am a student.'",
                tags=("romanian_basics", "a_fi_present"),
                hint="Start with 'I am'.",
            ),
        ),
    ),
    "nouns_and_articles": FallbackLessonTemplate(
        explanation_text="Romanian often adds the definite article to the end of the noun instead of putting a separate word before it.",
        key_rules=(
            "Masculine singular nouns often take '-ul' in the definite form.",
            "The article is attached to the noun, so the noun form changes instead of adding a separate 'the'.",
        ),
        example_sentences=(
            ExampleSentence(romanian="Baiatul este aici.", english="The boy is here."),
            ExampleSentence(romanian="Casa este mare.", english="The house is big."),
        ),
        questions=(
            FallbackQuestionTemplate(
                prompt="Choose the correct form for 'the boy'.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("baiat", "baiatul", "baieti", "baietul"),
                correct_answer="baiatul",
                explanation="The masculine singular definite form is 'baiatul'.",
                tags=("nouns_and_articles", "definite_articles"),
                hint="Pick the singular definite ending.",
            ),
            FallbackQuestionTemplate(
                prompt="Fill in the blank: ___ este mare. Use the definite form of 'casa'.",
                question_type=QuestionType.FILL_IN_THE_BLANK,
                correct_answer="Casa",
                explanation="'Casa' already carries the definite article for this noun.",
                tags=("nouns_and_articles", "definite_articles"),
                hint="This feminine noun keeps the same visible form here.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into English: Cadoul este nou.",
                question_type=QuestionType.ROMANIAN_TO_ENGLISH,
                correct_answer="The gift is new.",
                explanation="'Cadoul' means 'the gift'.",
                tags=("nouns_and_articles", "noun_gender"),
                hint="Focus on the definite noun first.",
            ),
            FallbackQuestionTemplate(
                prompt="Choose the indefinite noun.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("pomul", "casa", "cadoul", "baiatul"),
                correct_answer="casa",
                explanation="'Casa' can function as the base noun here, while the other options are marked definite forms.",
                tags=("nouns_and_articles", "definite_articles"),
                hint="Find the form without a masculine definite ending.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into Romanian: the gift",
                question_type=QuestionType.ENGLISH_TO_ROMANIAN,
                correct_answer="cadoul",
                explanation="Romanian attaches the article to the noun: 'cadou' becomes 'cadoul'.",
                tags=("nouns_and_articles", "definite_articles"),
                hint="Add the masculine singular definite ending.",
            ),
        ),
    ),
    "core_cases": FallbackLessonTemplate(
        explanation_text="Core Romanian case work begins with noticing who receives an action and how article endings change in simple genitive and dative phrases.",
        key_rules=(
            "The direct object often appears without extra marking in simple accusative patterns.",
            "Genitive and dative phrases commonly use forms such as 'baiatului' in guided beginner examples.",
        ),
        example_sentences=(
            ExampleSentence(romanian="Vad fata.", english="I see the girl."),
            ExampleSentence(romanian="Dau cartea baiatului.", english="I give the book to the boy."),
        ),
        questions=(
            FallbackQuestionTemplate(
                prompt="Who receives the book in 'Dau cartea baiatului'?",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("cartea", "baiatului", "dau", "eu"),
                correct_answer="baiatului",
                explanation="'Baiatului' is the indirect object receiving the book.",
                tags=("core_cases", "dative"),
                hint="Look for the receiver of the action.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into Romanian: I see the house.",
                question_type=QuestionType.ENGLISH_TO_ROMANIAN,
                correct_answer="Vad casa.",
                explanation="'Vad casa' is a simple accusative pattern.",
                tags=("core_cases", "accusative"),
                hint="Use the same structure as 'I see the girl'.",
            ),
            FallbackQuestionTemplate(
                prompt="Fill in the blank: Dau floarea ___ . Use 'fetei'.",
                question_type=QuestionType.FILL_IN_THE_BLANK,
                correct_answer="fetei",
                explanation="'Fetei' marks the receiver in a simple dative phrase.",
                tags=("core_cases", "dative"),
                hint="Use the indirect object form.",
            ),
            FallbackQuestionTemplate(
                prompt="Choose the phrase that shows possession.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("vad cartea", "cartea fetei", "dau cartea", "este carte"),
                correct_answer="cartea fetei",
                explanation="'Cartea fetei' means 'the girl's book' and shows a genitive relationship.",
                tags=("core_cases", "genitive"),
                hint="Look for the phrase meaning 'of the girl'.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into English: Dau apa copilului.",
                question_type=QuestionType.ROMANIAN_TO_ENGLISH,
                correct_answer="I give water to the child.",
                explanation="'Copilului' is the receiver, so the sentence means 'to the child'.",
                tags=("core_cases", "dative"),
                hint="Identify the receiver of the action.",
            ),
        ),
    ),
    "present_tense_verbs": FallbackLessonTemplate(
        explanation_text="Romanian present tense verbs change with the subject, so learners need to match the ending to the person and number.",
        key_rules=(
            "The subject and verb must agree, as in 'eu vorbesc' and 'noi vorbim'.",
            "High-frequency verbs should be practised in short, realistic daily sentences first.",
        ),
        example_sentences=(
            ExampleSentence(romanian="Eu invat romana.", english="I study Romanian."),
            ExampleSentence(romanian="Noi mergem la scoala.", english="We go to school."),
        ),
        questions=(
            FallbackQuestionTemplate(
                prompt="Choose the correct form: Eu ___ romana.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("invata", "invat", "invatam", "invatati"),
                correct_answer="invat",
                explanation="'Eu' takes the first-person singular form 'invat'.",
                tags=("present_tense_verbs", "present_tense"),
                hint="Match the verb to 'eu'.",
            ),
            FallbackQuestionTemplate(
                prompt="Fill in the blank: Noi ___ acasa. Use the present tense of 'a merge'.",
                question_type=QuestionType.FILL_IN_THE_BLANK,
                correct_answer="mergem",
                explanation="'Noi mergem' means 'we go'.",
                tags=("present_tense_verbs", "agreement"),
                hint="Use the first-person plural form.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into Romanian: They work today.",
                question_type=QuestionType.ENGLISH_TO_ROMANIAN,
                correct_answer="Ei lucreaza astazi.",
                explanation="'Ei lucreaza astazi.' is a standard present-tense sentence.",
                tags=("present_tense_verbs", "present_tense"),
                hint="Use the third-person plural verb form.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into English: Tu citesti mult.",
                question_type=QuestionType.ROMANIAN_TO_ENGLISH,
                correct_answer="You read a lot.",
                explanation="'Tu citesti mult.' means 'You read a lot.'",
                tags=("present_tense_verbs", "agreement"),
                hint="Start with 'You'.",
            ),
            FallbackQuestionTemplate(
                prompt="Choose the verb form that agrees with 'noi'.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("scriu", "scrie", "scriem", "scrii"),
                correct_answer="scriem",
                explanation="'Noi scriem' is the correct agreement pattern.",
                tags=("present_tense_verbs", "agreement"),
                hint="Look for the first-person plural form.",
            ),
        ),
    ),
    "pronouns_and_tenses": FallbackLessonTemplate(
        explanation_text="At A2, Romanian lessons combine basic pronouns with practical tense expansion such as the perfect compound and near-future forms.",
        key_rules=(
            "Object pronouns should stay close to the verb in simple learner-safe examples.",
            "The perfect compound uses forms of 'a avea' plus the past participle in common everyday contexts.",
        ),
        example_sentences=(
            ExampleSentence(romanian="Il vad pe Andrei.", english="I see Andrei."),
            ExampleSentence(romanian="Am mancat deja.", english="I have already eaten."),
        ),
        questions=(
            FallbackQuestionTemplate(
                prompt="Choose the correct object pronoun for a masculine singular noun.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("o", "ii", "il", "le"),
                correct_answer="il",
                explanation="'Il' is a common direct object pronoun for a masculine singular referent.",
                tags=("pronouns_and_tenses", "object_pronouns"),
                hint="Pick the masculine singular object form.",
            ),
            FallbackQuestionTemplate(
                prompt="Fill in the blank: Eu ___ plecat. Use the perfect compound auxiliary.",
                question_type=QuestionType.FILL_IN_THE_BLANK,
                correct_answer="am",
                explanation="'Am plecat' is the first-person singular perfect compound form.",
                tags=("pronouns_and_tenses", "perfect_compound"),
                hint="Use the auxiliary for 'eu'.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into Romanian: I will call her tomorrow.",
                question_type=QuestionType.ENGLISH_TO_ROMANIAN,
                correct_answer="O sa o sun maine.",
                explanation="'O sa o sun maine.' is a common near-future form with an object pronoun.",
                tags=("pronouns_and_tenses", "future"),
                hint="Use the common near-future pattern.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into English: Ne vedem diseara.",
                question_type=QuestionType.ROMANIAN_TO_ENGLISH,
                correct_answer="We will see each other this evening.",
                explanation="'Ne vedem diseara.' is a practical reflexive expression.",
                tags=("pronouns_and_tenses", "subject_pronouns"),
                hint="Think of a reciprocal action.",
            ),
            FallbackQuestionTemplate(
                prompt="Choose the correct completion: Ieri ___ cumparat paine.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("am", "voi", "este", "sunt"),
                correct_answer="am",
                explanation="A completed action yesterday takes the perfect compound auxiliary 'am'.",
                tags=("pronouns_and_tenses", "perfect_compound"),
                hint="Use the auxiliary for a past completed action.",
            ),
        ),
    ),
    "connected_communication": FallbackLessonTemplate(
        explanation_text="Connected everyday communication links short Romanian clauses with time markers, sequencing phrases, adverbs, and practical commands.",
        key_rules=(
            "Sequencing words such as 'apoi' and 'dupa aceea' help learners connect short actions clearly.",
            "Imperatives in beginner contexts should stay short, direct, and realistic.",
        ),
        example_sentences=(
            ExampleSentence(romanian="Mai intai mananc, apoi plec.", english="First I eat, then I leave."),
            ExampleSentence(romanian="Vino aici acum.", english="Come here now."),
        ),
        questions=(
            FallbackQuestionTemplate(
                prompt="Choose the best sequencing word for 'then'.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("ieri", "apoi", "nici", "mereu"),
                correct_answer="apoi",
                explanation="'Apoi' is a common sequencing word meaning 'then'.",
                tags=("connected_communication", "sequencing"),
                hint="Choose the connector that links actions in order.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into Romanian: Speak slowly, please.",
                question_type=QuestionType.ENGLISH_TO_ROMANIAN,
                correct_answer="Vorbeste incet, te rog.",
                explanation="'Vorbeste incet, te rog.' is a clear imperative with an adverb.",
                tags=("connected_communication", "imperative"),
                hint="Use an imperative plus an adverb.",
            ),
            FallbackQuestionTemplate(
                prompt="Fill in the blank: El merge ___ decat mine. Use the comparative adverb.",
                question_type=QuestionType.FILL_IN_THE_BLANK,
                correct_answer="mai repede",
                explanation="'Mai repede' expresses 'faster' in a simple comparison.",
                tags=("connected_communication", "comparisons"),
                hint="Use the pattern for 'more quickly'.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into English: Dupa aceea mergem la magazin.",
                question_type=QuestionType.ROMANIAN_TO_ENGLISH,
                correct_answer="After that we go to the shop.",
                explanation="'Dupa aceea' means 'after that'.",
                tags=("connected_communication", "sequencing"),
                hint="Begin with 'After that'.",
            ),
            FallbackQuestionTemplate(
                prompt="Choose the sentence that sounds like a direct instruction.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("Eu citesc acum.", "Noi mergem maine.", "Deschide usa, te rog.", "Ei vin tarziu."),
                correct_answer="Deschide usa, te rog.",
                explanation="An imperative gives a direct instruction.",
                tags=("connected_communication", "imperative"),
                hint="Look for the command form.",
            ),
        ),
    ),
}


class ContentLibrary:
    def __init__(
        self,
        topics: tuple[TopicMetadata, ...] = ROADMAP_TOPICS,
        placement_blueprint: tuple[PlacementTestSection, ...] = PLACEMENT_TEST_BLUEPRINT,
    ) -> None:
        self._topics = tuple(sorted(topics, key=lambda topic: topic.level))
        self._topics_by_id = {topic.topic_id: topic for topic in topics}
        self._placement_blueprint = placement_blueprint
        self._validate_topics()
        self._validate_placement_blueprint()

    def all_topics(self) -> tuple[TopicMetadata, ...]:
        return self._topics

    def get_topic(self, topic_id: str) -> TopicMetadata | None:
        return self._topics_by_id.get(topic_id)

    def topics_for_band(self, cefr_band: CEFRBand) -> tuple[TopicMetadata, ...]:
        return tuple(topic for topic in self._topics if topic.cefr_band == cefr_band)

    def placement_blueprint(self) -> tuple[PlacementTestSection, ...]:
        return self._placement_blueprint

    def supports_fallback(self, topic_id: str) -> bool:
        return topic_id in FALLBACK_LESSON_TEMPLATES

    def build_fallback_lesson(
        self,
        topic_id: str,
        *,
        difficulty: int,
        question_count: int,
        session_goal: str = "lesson",
    ) -> Lesson:
        topic = self._require_topic(topic_id)
        template = FALLBACK_LESSON_TEMPLATES.get(topic_id)
        if template is None:
            raise ValueError(f"No fallback template is available for topic '{topic_id}'.")
        normalized_difficulty = max(1, min(10, difficulty))
        questions: list[Question] = []
        for index in range(question_count):
            base = template.questions[index % len(template.questions)]
            variant = index // len(template.questions)
            suffix = f"-v{variant + 1}" if variant else ""
            prompt_suffix = f" Variant {variant + 1}." if variant else ""
            questions.append(
                Question(
                    question_id=f"fallback-{topic_id}-q{index + 1}{suffix}",
                    prompt=f"{base.prompt}{prompt_suffix}",
                    question_type=base.question_type,
                    difficulty_rating=normalized_difficulty,
                    cefr_band=topic.cefr_band,
                    correct_answer=base.correct_answer,
                    explanation=base.explanation,
                    tags=list(base.tags),
                    options=list(base.options),
                    hint=base.hint,
                    rubric=dict(base.rubric or {}),
                )
            )
        return Lesson(
            lesson_id=f"fallback-{topic_id}-{session_goal}-d{normalized_difficulty}",
            topic=topic.topic_id,
            level=topic.level,
            cefr_band=topic.cefr_band,
            difficulty=normalized_difficulty,
            explanation_text=template.explanation_text,
            example_sentences=list(template.example_sentences),
            key_rules=list(template.key_rules),
            quiz_questions=questions,
        )

    def target_cefr_band(self, level: int) -> CEFRBand:
        if level < 1:
            raise ValueError("Level must be at least 1.")
        candidate = self._topics[-1]
        for topic in self._topics:
            if level <= topic.level:
                candidate = topic
                break
        return candidate.cefr_band

    def available_topics(
        self,
        mastery_matrix: Mapping[str, float],
        mastery_threshold: float = 0.75,
    ) -> tuple[TopicMetadata, ...]:
        self._validate_mastery_threshold(mastery_threshold)
        return tuple(
            topic
            for topic in self._topics
            if all(mastery_matrix.get(prerequisite, 0.0) >= mastery_threshold for prerequisite in topic.prerequisites)
        )

    def next_topic_for_user(
        self,
        user_progress: UserProgress,
        mastery_threshold: float = 0.75,
    ) -> TopicMetadata | None:
        self._validate_mastery_threshold(mastery_threshold)
        mastery_matrix = user_progress.mastery_matrix
        for topic in self._topics:
            score = mastery_matrix.get(topic.topic_id, 0.0)
            if score >= mastery_threshold:
                continue
            blocking_topic = self._first_unmastered_prerequisite(topic, mastery_matrix, mastery_threshold)
            if blocking_topic is not None:
                return blocking_topic
            return topic
        return None

    def blocking_topics_for_user(
        self,
        topic_id: str,
        user_progress: UserProgress,
        mastery_threshold: float = 0.75,
        b2_prerequisite_threshold: float = 0.8,
    ) -> tuple[TopicMetadata, ...]:
        self._validate_mastery_threshold(mastery_threshold)
        self._validate_mastery_threshold(b2_prerequisite_threshold)
        topic = self._require_topic(topic_id)
        mastery_matrix = user_progress.mastery_matrix
        blocking_topics: list[TopicMetadata] = []
        seen: set[str] = set()

        def visit(candidate: TopicMetadata, threshold: float) -> None:
            for prerequisite_id in candidate.prerequisites:
                prerequisite = self._topics_by_id[prerequisite_id]
                visit(prerequisite, threshold)
                if mastery_matrix.get(prerequisite_id, 0.0) < threshold and prerequisite_id not in seen:
                    blocking_topics.append(prerequisite)
                    seen.add(prerequisite_id)

        visit(topic, mastery_threshold)
        if topic.cefr_band == CEFRBand.B2:
            for b1_topic in self.topics_for_band(CEFRBand.B1):
                if mastery_matrix.get(b1_topic.topic_id, 0.0) < b2_prerequisite_threshold and b1_topic.topic_id not in seen:
                    blocking_topics.append(b1_topic)
                    seen.add(b1_topic.topic_id)
        return tuple(blocking_topics)

    def is_topic_unlocked(
        self,
        topic_id: str,
        user_progress: UserProgress,
        mastery_threshold: float = 0.75,
        b2_prerequisite_threshold: float = 0.8,
    ) -> bool:
        return not self.blocking_topics_for_user(
            topic_id=topic_id,
            user_progress=user_progress,
            mastery_threshold=mastery_threshold,
            b2_prerequisite_threshold=b2_prerequisite_threshold,
        )

    def _first_unmastered_prerequisite(
        self,
        topic: TopicMetadata,
        mastery_matrix: Mapping[str, float],
        mastery_threshold: float,
    ) -> TopicMetadata | None:
        for prerequisite_id in topic.prerequisites:
            prerequisite = self._topics_by_id[prerequisite_id]
            blocking_topic = self._first_unmastered_prerequisite(prerequisite, mastery_matrix, mastery_threshold)
            if blocking_topic is not None:
                return blocking_topic
            if mastery_matrix.get(prerequisite_id, 0.0) < mastery_threshold:
                return prerequisite
        return None

    def _validate_mastery_threshold(self, mastery_threshold: float) -> None:
        if not 0.0 <= mastery_threshold <= 1.0:
            raise ValueError("Mastery threshold must be between 0.0 and 1.0.")

    def _require_topic(self, topic_id: str) -> TopicMetadata:
        topic = self.get_topic(topic_id)
        if topic is None:
            raise ValueError(f"Unknown topic '{topic_id}'.")
        return topic

    def _validate_topics(self) -> None:
        if len(self._topics_by_id) != len(self._topics):
            raise ValueError("Topic ids must be unique.")
        expected_levels = list(range(1, len(self._topics) + 1))
        actual_levels = [topic.level for topic in self._topics]
        if actual_levels != expected_levels:
            raise ValueError("Roadmap levels must be contiguous and start at 1.")
        for topic in self._topics:
            for prerequisite_id in topic.prerequisites:
                if prerequisite_id not in self._topics_by_id:
                    raise ValueError(f"Unknown prerequisite '{prerequisite_id}' for topic '{topic.topic_id}'.")
                if self._topics_by_id[prerequisite_id].level >= topic.level:
                    raise ValueError("Prerequisites must point to earlier levels.")

    def _validate_placement_blueprint(self) -> None:
        if not self._placement_blueprint:
            raise ValueError("Placement blueprint cannot be empty.")
        topic_ids = {topic.topic_id for topic in self._topics}
        covered_bands = {section.cefr_band for section in self._placement_blueprint}
        if covered_bands != {CEFRBand.A1, CEFRBand.A2, CEFRBand.B1, CEFRBand.B2}:
            raise ValueError("Placement blueprint must cover A1, A2, B1, and B2.")
        for section in self._placement_blueprint:
            if section.question_count < 1:
                raise ValueError("Placement sections must include at least one question.")
            low, high = section.target_difficulty
            if low < 1 or high > 10 or low > high:
                raise ValueError("Placement section difficulty ranges must fit within 1 to 10.")
            for topic_id in section.topic_ids:
                if topic_id not in topic_ids:
                    raise ValueError(f"Unknown placement topic '{topic_id}' in section '{section.section_id}'.")
