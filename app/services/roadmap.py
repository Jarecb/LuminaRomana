from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import random
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from app.storage import OfflineQuestionRepository


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
            FallbackQuestionTemplate(
                prompt="Choose the correct Romanian form of 'you are' for one person.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("sunt", "esti", "este", "suntem"),
                correct_answer="esti",
                explanation="'Tu esti' means 'you are' for one person.",
                tags=("romanian_basics", "a_fi_present"),
                hint="Pick the second-person singular form.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into Romanian: We are here.",
                question_type=QuestionType.ENGLISH_TO_ROMANIAN,
                correct_answer="Noi suntem aici.",
                explanation="'Noi suntem aici.' uses the first-person plural form of 'a fi'.",
                tags=("romanian_basics", "a_fi_present"),
                hint="Start with 'Noi'.",
            ),
            FallbackQuestionTemplate(
                prompt="Fill in the blank: El ___ acasa.",
                question_type=QuestionType.FILL_IN_THE_BLANK,
                correct_answer="este",
                explanation="'El este acasa.' uses the third-person singular form of 'a fi'.",
                tags=("romanian_basics", "a_fi_present"),
                hint="Use the form that means 'is'.",
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
            FallbackQuestionTemplate(
                prompt="Choose the correct form for 'the tree'.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("pom", "pomul", "pomi", "pomului"),
                correct_answer="pomul",
                explanation="'Pomul' is the masculine singular definite form meaning 'the tree'.",
                tags=("nouns_and_articles", "definite_articles"),
                hint="Look for the definite singular ending.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into English: Baiatul citeste.",
                question_type=QuestionType.ROMANIAN_TO_ENGLISH,
                correct_answer="The boy is reading.",
                explanation="'Baiatul' already includes the definite article, so it means 'the boy'.",
                tags=("nouns_and_articles", "definite_articles"),
                hint="Focus on the noun ending first.",
            ),
            FallbackQuestionTemplate(
                prompt="Fill in the blank with the definite form: ___ este pe masa. Use 'manual'.",
                question_type=QuestionType.FILL_IN_THE_BLANK,
                correct_answer="manualul",
                explanation="'Manualul' means 'the textbook' and shows the masculine definite ending '-ul'.",
                tags=("nouns_and_articles", "definite_articles"),
                hint="Add the attached definite article.",
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
            FallbackQuestionTemplate(
                prompt="Choose the phrase that means 'to the teacher'.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("profesorul", "profesorului", "profesor", "pe profesor"),
                correct_answer="profesorului",
                explanation="'Profesorului' is the dative-style form used for 'to the teacher' in guided examples.",
                tags=("core_cases", "dative"),
                hint="Look for the form used with a receiver.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into Romanian: The girl's book.",
                question_type=QuestionType.ENGLISH_TO_ROMANIAN,
                correct_answer="Cartea fetei.",
                explanation="'Cartea fetei.' shows possession with the genitive-style form 'fetei'.",
                tags=("core_cases", "genitive"),
                hint="Start with 'Cartea'.",
            ),
            FallbackQuestionTemplate(
                prompt="Fill in the blank: Ii dau scrisoarea ___ . Use 'mamei'.",
                question_type=QuestionType.FILL_IN_THE_BLANK,
                correct_answer="mamei",
                explanation="'Mamei' marks the receiver, so it fits the giving pattern here.",
                tags=("core_cases", "dative"),
                hint="Use the form for 'to the mother'.",
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
            FallbackQuestionTemplate(
                prompt="Choose the correct form: Ei ___ acolo.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("merg", "merge", "mergeti", "mergem"),
                correct_answer="merg",
                explanation="'Ei merg' is the correct third-person plural present form.",
                tags=("present_tense_verbs", "agreement"),
                hint="Pick the form for 'they'.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into Romanian: She learns quickly.",
                question_type=QuestionType.ENGLISH_TO_ROMANIAN,
                correct_answer="Ea invata repede.",
                explanation="'Ea invata repede.' matches the third-person singular subject with the correct verb form.",
                tags=("present_tense_verbs", "present_tense"),
                hint="Use the form for 'she'.",
            ),
            FallbackQuestionTemplate(
                prompt="Fill in the blank: Tu ___ romana foarte bine.",
                question_type=QuestionType.FILL_IN_THE_BLANK,
                correct_answer="vorbesti",
                explanation="'Tu vorbesti' uses the second-person singular ending.",
                tags=("present_tense_verbs", "agreement"),
                hint="Use the form for one person being addressed.",
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
            FallbackQuestionTemplate(
                prompt="Translate into English: Il chem maine.",
                question_type=QuestionType.ROMANIAN_TO_ENGLISH,
                correct_answer="I will call him tomorrow.",
                explanation="'Il' replaces a masculine direct object, so the sentence means 'I will call him tomorrow.'",
                tags=("pronouns_and_tenses", "object_pronouns"),
                hint="Start with the object pronoun.",
            ),
            FallbackQuestionTemplate(
                prompt="Choose the correct auxiliary: Noi ___ ajuns deja.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("am", "ati", "au", "ai"),
                correct_answer="am",
                explanation="In learner-safe perfect compound patterns, 'Noi am ajuns' is the expected form.",
                tags=("pronouns_and_tenses", "perfect_compound"),
                hint="Use the common auxiliary used before the participle.",
            ),
            FallbackQuestionTemplate(
                prompt="Fill in the blank: O ___ vad mai tarziu. Use the near-future helper.",
                question_type=QuestionType.FILL_IN_THE_BLANK,
                correct_answer="sa",
                explanation="'O sa vad' is the common near-future pattern.",
                tags=("pronouns_and_tenses", "future"),
                hint="Use the short future helper after 'o'.",
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
            FallbackQuestionTemplate(
                prompt="Choose the best word for 'after that'.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("mereu", "dupa aceea", "acum", "deja"),
                correct_answer="dupa aceea",
                explanation="'Dupa aceea' is a common sequencing phrase meaning 'after that'.",
                tags=("connected_communication", "sequencing"),
                hint="Pick the phrase that links the next action.",
            ),
            FallbackQuestionTemplate(
                prompt="Fill in the blank: Scrie mai ___, te rog.",
                question_type=QuestionType.FILL_IN_THE_BLANK,
                correct_answer="clar",
                explanation="'Mai clar' means 'more clearly' and fits an instruction with comparison.",
                tags=("connected_communication", "adverbs", "comparisons"),
                hint="Use an adverb that means 'clearly'.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into Romanian: First we eat, then we leave.",
                question_type=QuestionType.ENGLISH_TO_ROMANIAN,
                correct_answer="Mai intai mancam, apoi plecam.",
                explanation="'Mai intai ... apoi ...' is a standard way to sequence everyday actions.",
                tags=("connected_communication", "sequencing"),
                hint="Use the sequencing pair from the lesson examples.",
            ),
        ),
    ),
    "narrative_b1_grammar": FallbackLessonTemplate(
        explanation_text="B1 narrative Romanian links events across multiple sentences and asks the learner to control tense contrast, relative clauses, and practical meaning in context.",
        key_rules=(
            "Use the imperfect for background, repeated, or ongoing past context, and the perfect compound for completed foreground events.",
            "At B1, grammar tasks can combine tense contrast with connectors, obligation, motion, and relative-clause meaning inside one realistic scenario.",
        ),
        example_sentences=(
            ExampleSentence(
                romanian="Cind eram mic, mergeam des la bunici. Intr-o vara am stat acolo doua saptamini si am invatat sa pescuiesc.",
                english="When I was little, I used to go to my grandparents often. One summer I stayed there for two weeks and learned to fish.",
            ),
            ExampleSentence(
                romanian="Prietenul care locuieste la Cluj mi-a spus ca trebuie sa plece devreme, dar vrea sa revina miine.",
                english="The friend who lives in Cluj told me that he has to leave early, but he wants to come back tomorrow.",
            ),
        ),
        questions=(
            FallbackQuestionTemplate(
                prompt="Sentence transformation: Rewrite the idea using a background imperfect and a completed perfect compound action. Start from 'I was reading when Maria arrived.'",
                question_type=QuestionType.SENTENCE_TRANSFORMATION,
                correct_answer="Citeam cind a sosit Maria.",
                explanation="The imperfect 'citeam' sets the background action, while 'a sosit' marks the completed interrupting event.",
                tags=("narrative_b1_grammar", "imperfect", "perfect_compound_contrast"),
                hint="Use one ongoing past form and one completed past form.",
            ),
            FallbackQuestionTemplate(
                prompt="Dialogue completion: Complete the reply in Romanian. 'De ce nu vii cu noi la munte?' 'Nu pot, pentru ca ___ sa lucrez simbata.'",
                question_type=QuestionType.DIALOGUE_COMPLETION,
                correct_answer="trebuie",
                explanation="'Trebuie sa lucrez' expresses obligation, which fits the reason for not coming.",
                tags=("narrative_b1_grammar", "obligation"),
                hint="Use the common verb of obligation.",
            ),
            FallbackQuestionTemplate(
                prompt="Choose the sentence that correctly contrasts a repeated background action with one completed event.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=(
                    "Ieri citeam ziarul in fiecare dimineata.",
                    "Cind lucram in Brasov, am cunoscut multi clienti interesanti.",
                    "Cind am lucrat in Brasov, cunosteam multi clienti intr-o clipa.",
                    "Mergeam la gara si ajungeam ieri la ora opt.",
                ),
                correct_answer="Cind lucram in Brasov, am cunoscut multi clienti interesanti.",
                explanation="The imperfect 'lucram' gives the background period and the perfect compound 'am cunoscut' marks a completed event within it.",
                tags=("narrative_b1_grammar", "imperfect", "perfect_compound_contrast"),
                hint="Look for an ongoing background plus one finished event.",
            ),
            FallbackQuestionTemplate(
                prompt="Fill in the blank with the common relative connector: 'Fata ___ m-a ajutat ieri este sora lui Dan.'",
                question_type=QuestionType.FILL_IN_THE_BLANK,
                correct_answer="care",
                explanation="'Care' introduces the relative clause that identifies the girl.",
                tags=("narrative_b1_grammar", "relative_clauses"),
                hint="Use the connector meaning 'who'.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into Romanian: While we were walking to the station, it started to rain.",
                question_type=QuestionType.ENGLISH_TO_ROMANIAN,
                correct_answer="In timp ce mergeam spre gara, a inceput sa ploua.",
                explanation="The ongoing movement takes the imperfect 'mergeam', while the rain beginning is a completed event with 'a inceput'.",
                tags=("narrative_b1_grammar", "motion", "imperfect", "perfect_compound_contrast"),
                hint="Use an imperfect for the walk and a completed form for the start of the rain.",
            ),
        ),
    ),
    "b1_b2_transition": FallbackLessonTemplate(
        explanation_text="The transition beyond core B1 adds conditional politeness, denser clause linking, and controlled pronoun placement in messages and practical explanations.",
        key_rules=(
            "The conditional supports polite requests, preferences, and hypotheticals in practical communication.",
            "Subordinate clauses for cause, purpose, and contrast should stay coherent across two or more connected sentences.",
        ),
        example_sentences=(
            ExampleSentence(
                romanian="As vrea sa rezerv o camera pentru vineri, daca ar fi posibil. Vin tirziu pentru ca termin sedinta la sase.",
                english="I would like to book a room for Friday, if that were possible. I am arriving late because I finish the meeting at six.",
            ),
            ExampleSentence(
                romanian="Ti-am trimis documentele ca sa le poti verifica astazi, dar nu le-am pus in ultimul mesaj fiindca eram pe drum.",
                english="I sent you the documents so that you could check them today, but I did not put them in the last message because I was on the way.",
            ),
        ),
        questions=(
            FallbackQuestionTemplate(
                prompt="Dialogue completion: Complete the polite request. 'Buna ziua. ___ sa schimb rezervarea pentru luni, va rog.'",
                question_type=QuestionType.DIALOGUE_COMPLETION,
                correct_answer="As dori",
                explanation="'As dori' is a polite conditional form used for requests in service situations.",
                tags=("b1_b2_transition", "conditional", "register_awareness"),
                hint="Use a polite conditional phrase.",
            ),
            FallbackQuestionTemplate(
                prompt="Sentence transformation: Rewrite the direct request as a more polite Romanian conditional request. Start from 'Trimite-mi raportul azi.'",
                question_type=QuestionType.SENTENCE_TRANSFORMATION,
                correct_answer="Mi-ai trimite raportul azi?",
                explanation="The conditional request softens the imperative while keeping the same practical meaning.",
                tags=("b1_b2_transition", "conditional", "complex_pronouns"),
                hint="Turn the command into a polite question.",
            ),
            FallbackQuestionTemplate(
                prompt="Choose the connector that best expresses purpose: 'Iti scriu ___ sa stabilim ora intilnirii.'",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("desi", "ca sa", "pentru ca", "dar"),
                correct_answer="ca sa",
                explanation="'Ca sa' introduces a purpose clause: the message is written in order to set the meeting time.",
                tags=("b1_b2_transition", "subordinate_clauses"),
                hint="Pick the option meaning 'in order to'.",
            ),
            FallbackQuestionTemplate(
                prompt="Fill in the blank with the best connector of contrast: 'As veni mai devreme, ___ trenul acesta ajunge prea tirziu.'",
                question_type=QuestionType.FILL_IN_THE_BLANK,
                correct_answer="dar",
                explanation="'Dar' introduces a practical contrast between intention and reality.",
                tags=("b1_b2_transition", "subordinate_clauses", "register_awareness"),
                hint="Use a simple contrast connector.",
            ),
            FallbackQuestionTemplate(
                prompt="Translate into English: Ti l-as arata acum, dar nu il am la mine.",
                question_type=QuestionType.ROMANIAN_TO_ENGLISH,
                correct_answer="I would show it to you now, but I do not have it with me.",
                explanation="The sentence combines a conditional with object pronoun placement inside a realistic everyday explanation.",
                tags=("b1_b2_transition", "conditional", "complex_pronouns"),
                hint="Keep both pronouns in the translation.",
            ),
        ),
    ),
    "b2_core_structures": FallbackLessonTemplate(
        explanation_text="B2 lessons combine paragraph-level reading with connector control, reported speech, and modern passive or impersonal phrasing so the learner can interpret and produce extended meaning.",
        key_rules=(
            "At B2, connectors such as 'totusi', 'in plus', and 'prin urmare' help organise argument and comparison across a short paragraph.",
            "Reported speech and passive or impersonal structures should stay natural and support coherent reading or writing tasks rather than isolated sentence tricks.",
        ),
        example_sentences=(
            ExampleSentence(
                romanian="Compania a anuntat ieri ca proiectul va continua, desi costurile au crescut. Directorul a spus ca rezultatele vor fi analizate din nou, iar raportul final va fi trimis clientilor saptamina viitoare.",
                english="The company announced yesterday that the project will continue, although costs have increased. The director said that the results will be analysed again, and the final report will be sent to clients next week.",
            ),
            ExampleSentence(
                romanian="In oras se discuta tot mai des despre transportul public, deoarece traficul s-a agravat. Totusi, unii locuitori spun ca solutiile propuse ar fi utile numai daca ar fi aplicate consecvent.",
                english="In the city, public transport is being discussed more and more often because traffic has worsened. However, some residents say the proposed solutions would be useful only if they were applied consistently.",
            ),
        ),
        questions=(
            FallbackQuestionTemplate(
                prompt="Reading comprehension: Read the passage and answer in English. 'Compania a anuntat ieri ca proiectul va continua, desi costurile au crescut. Directorul a spus ca rezultatele vor fi analizate din nou, iar raportul final va fi trimis clientilor saptamina viitoare.' What will happen next week?",
                question_type=QuestionType.READING_COMPREHENSION,
                correct_answer="The final report will be sent to clients next week.",
                explanation="The final clause in the passage states directly that the report will be sent the following week.",
                tags=("b2_core_structures", "reported_speech", "advanced_connectors"),
                hint="Look at the end of the second sentence.",
            ),
            FallbackQuestionTemplate(
                prompt="Guided writing: Write two or three Romanian sentences giving your opinion about improving city transport. Use at least one connector of contrast or conclusion.",
                question_type=QuestionType.GUIDED_WRITING,
                correct_answer="Transportul public trebuie imbunatatit, deoarece traficul este tot mai dificil. Totusi, investitiile ar trebui planificate cu atentie. Prin urmare, orasul are nevoie de solutii clare si rapide.",
                explanation="A strong answer gives an opinion, supports it with a reason, and uses connectors such as 'totusi' or 'prin urmare' to organise the ideas.",
                tags=("b2_core_structures", "advanced_connectors", "guided_opinion"),
                hint="State an opinion, add one reason, then conclude clearly.",
                rubric={
                    "task_completion": "Gives a clear opinion and supports it with relevant detail.",
                    "connector_control": "Uses at least one discourse marker appropriately.",
                    "grammar_control": "Keeps tense, agreement, and sentence linking mostly consistent.",
                },
            ),
            FallbackQuestionTemplate(
                prompt="Choose the best connector to complete the argument: 'Traficul este mai intens; ___, autoritatile cauta solutii pentru transportul public.'",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=("prin urmare", "de exemplu", "poate", "altadata"),
                correct_answer="prin urmare",
                explanation="'Prin urmare' expresses a conclusion that follows from the previous statement.",
                tags=("b2_core_structures", "advanced_connectors"),
                hint="Choose the connector that means 'therefore'.",
            ),
            FallbackQuestionTemplate(
                prompt="Sentence transformation: Rewrite the idea using reported speech. Start from 'Maria: Plec miine dimineata.'",
                question_type=QuestionType.SENTENCE_TRANSFORMATION,
                correct_answer="Maria a spus ca pleaca a doua zi dimineata.",
                explanation="Reported speech shifts the statement into an indirect clause introduced by 'ca'.",
                tags=("b2_core_structures", "reported_speech"),
                hint="Begin with 'Maria a spus ca...'.",
            ),
            FallbackQuestionTemplate(
                prompt="Fill in the blank with a natural impersonal or passive-style form: 'In acest raport ___ analizate trei variante principale.'",
                question_type=QuestionType.FILL_IN_THE_BLANK,
                correct_answer="sint",
                explanation="'Sint analizate' creates a natural passive-style statement suited to formal Romanian explanation.",
                tags=("b2_core_structures", "passive_voice", "impersonal_forms"),
                hint="Use the helper that forms a passive-style statement.",
            ),
        ),
    ),
    "b2_consolidation": FallbackLessonTemplate(
        explanation_text="B2 consolidation asks the learner to read, evaluate, and produce connected Romanian that combines tense choice, connectors, case awareness, and explanation or justification in one task set.",
        key_rules=(
            "B2 consolidation should mix several high-frequency grammar patterns inside realistic discourse rather than testing one isolated form at a time.",
            "Reading and writing tasks at this stage should require explanation, comparison, justification, or error correction with multiple interacting cues.",
        ),
        example_sentences=(
            ExampleSentence(
                romanian="Anul trecut lucram intr-o echipa mica, dar intre timp compania s-a extins, iar responsabilitatile mele s-au schimbat considerabil. Acum trebuie sa explic deciziile mai clar, pentru ca proiectele sint urmarite de mai multi parteneri.",
                english="Last year I was working in a small team, but in the meantime the company expanded, and my responsibilities changed considerably. Now I have to explain decisions more clearly because the projects are followed by more partners.",
            ),
            ExampleSentence(
                romanian="Unii candidati spun ca programul online este mai flexibil, in timp ce altii prefera cursurile fata in fata, deoarece primesc feedback imediat. In opinia mea, varianta potrivita depinde de ritmul de lucru si de obiectivele fiecaruia.",
                english="Some candidates say the online programme is more flexible, while others prefer face-to-face courses because they receive immediate feedback. In my opinion, the right option depends on each person's working pace and goals.",
            ),
        ),
        questions=(
            FallbackQuestionTemplate(
                prompt="Reading comprehension: Read the passage and answer in English. 'Unii candidati spun ca programul online este mai flexibil, in timp ce altii prefera cursurile fata in fata, deoarece primesc feedback imediat. In opinia mea, varianta potrivita depinde de ritmul de lucru si de obiectivele fiecaruia.' According to the writer, what should determine the best option?",
                question_type=QuestionType.READING_COMPREHENSION,
                correct_answer="The best option should depend on each person's working pace and goals.",
                explanation="The final sentence gives the writer's conclusion directly.",
                tags=("b2_consolidation", "advanced_connectors", "integrated_writing"),
                hint="Read the final clause of the passage.",
            ),
            FallbackQuestionTemplate(
                prompt="Guided writing: Write a short Romanian response comparing online and face-to-face study. Give your opinion and justify it in two or three connected sentences.",
                question_type=QuestionType.GUIDED_WRITING,
                correct_answer="Cursurile online sint mai flexibile si utile pentru persoanele care au un program incarcat. Totusi, cursurile fata in fata ofera feedback mai rapid si interactiune directa. Eu prefer varianta mixta, deoarece combina avantajele ambelor optiuni.",
                explanation="A strong answer compares both options, gives a personal preference, and justifies it with clear connected reasoning.",
                tags=("b2_consolidation", "integrated_writing", "advanced_connectors"),
                hint="Compare both options, then give and justify your preference.",
                rubric={
                    "comparison": "Compares at least two options clearly.",
                    "justification": "Explains the opinion with a relevant reason.",
                    "cohesion": "Uses connectors to link ideas into a short coherent response.",
                },
            ),
            FallbackQuestionTemplate(
                prompt="Error identification: Which segment contains the main grammar problem? 'Desi raportul a fost trimis ieri, clientii spune ca nu l-au primit inca.'",
                question_type=QuestionType.ERROR_IDENTIFICATION,
                options=("Desi raportul", "a fost trimis", "clientii spune", "nu l-au primit"),
                correct_answer="clientii spune",
                explanation="The plural subject 'clientii' needs the plural verb form 'spun', not 'spune'.",
                tags=("b2_consolidation", "agreement", "error_correction"),
                hint="Look for the mismatch between subject and verb.",
            ),
            FallbackQuestionTemplate(
                prompt="Sentence transformation: Rewrite the sentence to emphasise justification. Start from 'Am ales varianta online. Este mai flexibila pentru programul meu.'",
                question_type=QuestionType.SENTENCE_TRANSFORMATION,
                correct_answer="Am ales varianta online, deoarece este mai flexibila pentru programul meu.",
                explanation="The transformation links the choice and the reason into one coherent sentence with 'deoarece'.",
                tags=("b2_consolidation", "advanced_connectors", "integrated_writing"),
                hint="Join the ideas with a connector of reason.",
            ),
            FallbackQuestionTemplate(
                prompt="Dialogue completion: Complete the response in Romanian. 'De ce ai schimbat planul initial?' 'L-am schimbat, pentru ca intre timp ___ doua probleme noi si a trebuit sa aleg alta varianta.'",
                question_type=QuestionType.DIALOGUE_COMPLETION,
                correct_answer="au aparut",
                explanation="'Au aparut' fits the plural subject 'doua probleme noi' and explains the change of plan naturally.",
                tags=("b2_consolidation", "mixed_tenses", "integrated_writing"),
                hint="Use a completed past form agreeing with a plural subject.",
            ),
        ),
    ),
}

TOPIC_VOCABULARY: dict[str, tuple[tuple[str, str], ...]] = {
    "romanian_basics": (
        ("buna", "hello"),
        ("eu", "I"),
        ("tu", "you"),
        ("el", "he"),
        ("noi", "we"),
        ("sunt", "am / are"),
        ("esti", "are for one person addressed"),
        ("este", "is"),
        ("suntem", "are for we"),
        ("aici", "here"),
        ("student", "student"),
    ),
    "nouns_and_articles": (
        ("baiat", "boy"),
        ("baiatul", "the boy"),
        ("casa", "house / the house in this beginner pattern"),
        ("cadou", "gift"),
        ("cadoul", "the gift"),
        ("pom", "tree"),
        ("pomul", "the tree"),
        ("manual", "textbook"),
        ("manualul", "the textbook"),
        ("mare", "big"),
        ("nou", "new"),
    ),
    "core_cases": (
        ("cartea", "the book"),
        ("baiatului", "to the boy / of the boy"),
        ("fetei", "to the girl / of the girl"),
        ("copilului", "to the child"),
        ("mamei", "to the mother"),
        ("vad", "I see"),
        ("dau", "I give"),
        ("apa", "water"),
        ("floarea", "the flower"),
        ("scrisoarea", "the letter"),
        ("lui", "of / to him in common beginner patterns"),
    ),
    "present_tense_verbs": (
        ("invat", "I learn / study"),
        ("invata", "he or she learns"),
        ("vorbesti", "you speak"),
        ("merg", "they go / I go depending on subject"),
        ("mergem", "we go"),
        ("scriem", "we write"),
        ("citesti", "you read"),
        ("lucreaza", "they work / he works in common beginner spelling"),
        ("repede", "quickly"),
        ("romana", "Romanian"),
        ("acasa", "home"),
    ),
    "pronouns_and_tenses": (
        ("il", "him"),
        ("o", "her / it"),
        ("am", "have, used as a perfect tense helper"),
        ("sa", "to, used in future patterns after 'o'"),
        ("plecat", "left / gone"),
        ("sun", "I call"),
        ("maine", "tomorrow"),
        ("deja", "already"),
        ("ne", "us / each other"),
        ("vedem", "we see / we see each other"),
        ("diseara", "this evening"),
    ),
    "connected_communication": (
        ("mai intai", "first"),
        ("apoi", "then"),
        ("dupa aceea", "after that"),
        ("vorbeste", "speak"),
        ("incet", "slowly"),
        ("te rog", "please"),
        ("mai repede", "faster / more quickly"),
        ("vino", "come"),
        ("aici", "here"),
        ("acum", "now"),
        ("deschide", "open"),
        ("usa", "the door"),
    ),
    "narrative_b1_grammar": (
        ("cind eram", "when I was"),
        ("mergeam", "I was going / used to go"),
        ("am ajuns", "I arrived / have arrived"),
        ("a inceput", "it started"),
        ("trebuie", "must / have to"),
        ("voia", "wanted"),
        ("care", "who / which"),
        ("in timp ce", "while"),
        ("spre gara", "toward the station"),
        ("bunici", "grandparents"),
        ("ploua", "to rain"),
    ),
    "b1_b2_transition": (
        ("as dori", "I would like"),
        ("as vrea", "I would want / would like"),
        ("ca sa", "in order to"),
        ("pentru ca", "because"),
        ("desi", "although"),
        ("dar", "but"),
        ("rezervare", "booking / reservation"),
        ("sedinta", "meeting"),
        ("documente", "documents"),
        ("ti l-as arata", "I would show it to you"),
        ("la mine", "with me"),
    ),
    "b2_core_structures": (
        ("prin urmare", "therefore"),
        ("totusi", "however"),
        ("raportul final", "the final report"),
        ("vor fi analizate", "will be analysed"),
        ("clientilor", "to the clients"),
        ("se discuta", "it is discussed / people discuss"),
        ("solutii propuse", "proposed solutions"),
        ("consecvent", "consistently"),
        ("a spus ca", "said that"),
        ("transport public", "public transport"),
        ("opinie", "opinion"),
    ),
    "b2_consolidation": (
        ("feedback imediat", "immediate feedback"),
        ("varianta potrivita", "the right option"),
        ("depinde de", "depends on"),
        ("obiectivele fiecaruia", "each person's goals"),
        ("s-a extins", "expanded"),
        ("responsabilitati", "responsibilities"),
        ("intre timp", "in the meantime"),
        ("a aparut", "appeared"),
        ("deoarece", "because"),
        ("varianta mixta", "mixed option"),
        ("a justifica", "to justify"),
    ),
}


class ContentLibrary:
    def __init__(
        self,
        topics: tuple[TopicMetadata, ...] = ROADMAP_TOPICS,
        placement_blueprint: tuple[PlacementTestSection, ...] = PLACEMENT_TEST_BLUEPRINT,
        offline_question_repository: "OfflineQuestionRepository | None" = None,
    ) -> None:
        self._topics = tuple(sorted(topics, key=lambda topic: topic.level))
        self._topics_by_id = {topic.topic_id: topic for topic in topics}
        self._placement_blueprint = placement_blueprint
        self._offline_question_repository = offline_question_repository
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

    def vocabulary_for_topic(self, topic_id: str) -> tuple[tuple[str, str], ...]:
        self._require_topic(topic_id)
        return TOPIC_VOCABULARY.get(topic_id, ())

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
        question_templates = self._fallback_question_pool(topic_id, template.questions)
        selected_templates = self._select_fallback_questions(question_templates, question_count)
        questions: list[Question] = []
        for index, base in enumerate(selected_templates, start=1):
            questions.append(
                Question(
                    question_id=f"fallback-{topic_id}-q{index}",
                    prompt=base.prompt,
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

    def _select_fallback_questions(
        self,
        templates: tuple[FallbackQuestionTemplate, ...],
        question_count: int,
    ) -> list[FallbackQuestionTemplate]:
        if question_count <= len(templates):
            return random.sample(list(templates), question_count)
        selected = list(templates)
        while len(selected) < question_count:
            selected.extend(random.sample(list(templates), len(templates)))
        return selected[:question_count]

    def _fallback_question_pool(
        self,
        topic_id: str,
        templates: tuple[FallbackQuestionTemplate, ...],
    ) -> tuple[FallbackQuestionTemplate, ...]:
        combined: list[FallbackQuestionTemplate] = list(templates)
        if self._offline_question_repository is not None:
            combined.extend(
                self._question_to_template(question)
                for question in self._offline_question_repository.list_for_topic(topic_id)
            )

        deduped: list[FallbackQuestionTemplate] = []
        seen: set[tuple[str, str, str]] = set()
        for template in combined:
            key = (
                template.question_type.value,
                template.prompt.strip().casefold(),
                template.correct_answer.strip().casefold(),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(template)
        return tuple(deduped)

    def _question_to_template(self, question: Question) -> FallbackQuestionTemplate:
        return FallbackQuestionTemplate(
            prompt=question.prompt,
            question_type=question.question_type,
            correct_answer=question.correct_answer,
            explanation=question.explanation,
            tags=tuple(question.tags),
            options=tuple(question.options),
            hint=question.hint,
            rubric=dict(question.rubric),
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
