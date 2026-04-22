"""Constants and curated data for the learning service.

This module isolates large constant structures so the main service module stays focused.
"""
from __future__ import annotations

import re

DEFAULT_USER_ID = "default-learner"
PASSING_SCORE = 80.0
MIN_ATTEMPTS_TO_ADVANCE = 5
QUESTION_SET_COOLDOWN = 5
WORD_TOKEN_PATTERN = re.compile(r"[A-Za-zĂÂÎȘȚăâîșțŞŢşţ]+(?:[-'][A-Za-zĂÂÎȘȚăâîșțŞŢşţ]+)*")
QUOTED_TEXT_PATTERN = re.compile(r"['\"](?P<text>[^'\"]{2,})['\"]")
CURATED_VERB_CONJUGATIONS: dict[str, tuple[dict[str, object], str]] = {
    "sunt": (
        {
            "infinitive": "a fi",
            "present": {"eu": "sunt", "tu": "esti", "el/ea": "este", "noi": "suntem", "voi": "sinteti", "ei/ele": "sint"},
            "past": {"eu": "am fost", "el/ea": "a fost"},
            "future": {"eu": "voi fi", "el/ea": "va fi"},
            "participle": "fost",
            "gerund": "fiind",
        },
        "to be",
    ),
    "esti": (
        {
            "infinitive": "a fi",
            "present": {"eu": "sunt", "tu": "esti", "el/ea": "este", "noi": "suntem", "voi": "sinteti", "ei/ele": "sint"},
            "past": {"eu": "am fost", "el/ea": "a fost"},
            "future": {"eu": "voi fi", "el/ea": "va fi"},
            "participle": "fost",
            "gerund": "fiind",
        },
        "to be",
    ),
    "este": (
        {
            "infinitive": "a fi",
            "present": {"eu": "sunt", "tu": "esti", "el/ea": "este", "noi": "suntem", "voi": "sinteti", "ei/ele": "sint"},
            "past": {"eu": "am fost", "el/ea": "a fost"},
            "future": {"eu": "voi fi", "el/ea": "va fi"},
            "participle": "fost",
            "gerund": "fiind",
        },
        "to be",
    ),
    "suntem": (
        {
            "infinitive": "a fi",
            "present": {"eu": "sunt", "tu": "esti", "el/ea": "este", "noi": "suntem", "voi": "sinteti", "ei/ele": "sint"},
            "past": {"eu": "am fost", "el/ea": "a fost"},
            "future": {"eu": "voi fi", "el/ea": "va fi"},
            "participle": "fost",
            "gerund": "fiind",
        },
        "to be",
    ),
}

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
