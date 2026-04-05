# Lumina Romana

## Full Product and Test Specification

## Index
- [1. Purpose](#1-purpose)
- [2. Product Goals](#2-product-goals)
- [2.1 Current Implementation Baseline](#21-current-implementation-baseline)
- [3. Non-Goals](#3-non-goals)
- [4. Target Users](#4-target-users)
- [5. Core User Experience](#5-core-user-experience)
- [6. Learning Roadmap](#6-learning-roadmap)
- [7. Functional Requirements](#7-functional-requirements)
- [8. AI Content Generation](#8-ai-content-generation)
- [9. Content Validation Layer](#9-content-validation-layer)
- [10. Adaptive Difficulty Model](#10-adaptive-difficulty-model)
- [11. System Architecture](#11-system-architecture)
- [12. Python Technical Requirements](#12-python-technical-requirements)
- [13. Proposed Python Domain Model](#13-proposed-python-domain-model)
- [14. Persistence Model](#14-persistence-model)
- [15. AI Prompting Specification](#15-ai-prompting-specification)
- [16. Test Specification](#16-test-specification)
- [17. Error Handling](#17-error-handling)
- [18. Security and Privacy](#18-security-and-privacy)
- [19. Observability](#19-observability)
- [20. Future Enhancements](#20-future-enhancements)
- [21. Summary](#21-summary)

## 1. Purpose
Lumina Romana is a Python-based Romanian language learning application focused on structured grammar instruction and adaptive assessment. The system combines curated learning progression with AI-generated lessons and quizzes. AI is used to produce lesson content at scale, but all generated questions must remain sensible, pedagogically useful, and validated before they reach the learner.

The product is intended to teach Romanian grammar progressively, with specific attention to features that are difficult for English speakers:

- Romanian diacritics and pronunciation
- Three noun genders
- Suffix-based definite articles
- Core case usage
- Verb conjugation patterns

## 2. Product Goals
- Teach Romanian grammar in a clear sequence from beginner to intermediate topics.
- Support learner progression from absolute beginner through CEFR B2.
- Use AI to generate fresh lesson content, examples, and quizzes.
- Adapt lesson and quiz difficulty based on learner performance.
- Prevent low-quality or nonsensical AI output through structured validation.
- Track progress, mastery, and review needs over time.

## 2.1 Current Implementation Baseline
The implementation must remain consistent with the staged delivery plan in `plan.md`.

Completed plan stages as of 2026-04-05:

- Stage 0: Foundation and project setup
- Stage 1: Core domain model and local persistence
- Stage 2: Roadmap and curriculum engine
- Stage 3: Adaptive difficulty engine
- Stage 4: AI integration layer
- Stage 5: Validation and fallback content
- Stage 6: MVP learning loop
- Stage 7: B1 expansion
- Stage 8: B2 learning features
- Stage 9: Quality hardening
- Stage 10: Packaging and deployment
- Stage 11: Incorrect-answer mastery gate

This means the current baseline already includes:

- A Python project scaffold with package entrypoints, configuration loading, and logging
- Dataclass-based domain models for lessons, questions, quiz attempts, and user progress
- Local SQLite persistence for users, mastery, skills, lesson history, and quiz attempts
- A deterministic curriculum layer with Levels 1 through 10 mapped from A1 through B2
- Prerequisite-aware topic progression and a placement-test blueprint spanning A1 through B2
- Deterministic adaptive difficulty assessment, review-session planning, and prompt-constraint generation
- A provider-agnostic AI service boundary with an OpenAI-compatible provider implementation, environment-based configuration, metadata logging, and transient retry handling
- A validation layer that normalizes AI JSON into domain lessons, rejects off-scope or inconsistent content, retries with validation feedback, and falls back to curated templates for the supported A1-B2 roadmap topics
- A browser-based learning loop with a default local learner profile, CLI support commands, server-rendered web pages, per-level introductions, persisted question-set results, wordbank browsing, practice replay, and browser-based progress review
- Gemini support plus OpenAI-compatible provider support, including Copilot-style endpoints via provider aliasing
- Archival of validated AI-generated questions into a persistent offline question bank that expands the local fallback pool over time
- CLI maintenance flows for the offline question bank, including full-bank clearing and A1-B2 top-up seeding
- Stage 9 AI-quality metrics, prompt regression coverage, and a content-sampling workflow
- Stage 10 packaging and deployment assets including build metadata, a Windows startup script, and optional containerization
- Stage 11 persistent incorrect-answer tracking, remediation lessons before level advancement, and lesson-level duplicate-question prevention

Subsequent work defined in this specification must build on that baseline rather than re-specifying it as hypothetical. In particular, Stage 5 validation work should now integrate with the existing AI service and prompt builder instead of inventing a new content-generation entrypoint.

## 3. Non-Goals
- Full speech recognition in the first version
- Open-ended free conversation tutoring as a core feature
- Advanced literary Romanian, archaic forms, or dialect study
- Multiplayer or social features

## 4. Target Users
- English-speaking beginners learning Romanian
- Self-directed learners who want grammar explanations and drills
- Users who benefit from adaptive review and repeated exposure

## 5. Core User Experience
The learner starts with either:

- Level 1 by default, or
- A placement test that determines an initial level

The learner then progresses through short lesson units. Each unit includes:

- A pre-lesson explanation page describing the grammar principles for the level in plain English
- A grammar explanation
- Worked examples
- Vocabulary support
- A short quiz or question set

After each quiz, the system updates mastery scores and decides whether to:

- Advance the learner
- Keep difficulty stable
- Trigger a review session

The long-term progression target is B2. The learner experience must therefore support not only isolated grammar drills, but also cumulative practice with reading, listening-ready text prompts, structured writing prompts, and multi-step grammar integration appropriate for upper-intermediate learners.

For the current A1-A2 MVP loop, advancement through a roadmap topic should require repeated demonstrated control rather than a single strong attempt. The current baseline uses multiple question sets per topic and only advances after both the latest set and the running topic average meet the configured mastery threshold.

In the current baseline, score-based topic completion is still not sufficient on its own: if a learner has unresolved previously incorrect answers for the topic, the system serves a remediation set containing those pending questions and blocks advancement until they are later answered correctly.

## 6. Learning Roadmap
The app must teach Romanian in a controlled sequence. AI content generation must stay inside the current roadmap stage unless the adaptive engine explicitly advances the learner.

The roadmap must map cleanly onto CEFR-style bands. Internal numeric lesson levels may still be used, but the product must be able to report progress across the following proficiency targets:

- A1: survival phrases, basic sentence construction, present-tense essentials
- A2: everyday communication, common tense contrast, simple connected discourse
- B1: independent use in familiar contexts, narrative production, increased grammar integration
- B2: upper-intermediate control, nuanced sentence building, argumentation, and topic-flexible comprehension

### Level 1: Basics
- Romanian diacritics: `a, ă, â, î, s/ș, t/ț`
- Pronunciation and phonetic rules
- Basic greetings and introductions
- The verb `a fi` in the present tense

### Level 2: Nouns and Articles
- Masculine, feminine, and neuter nouns
- Singular and plural patterns at a beginner level
- Indefinite vs definite nouns
- Definite article suffixes such as `baiat -> baiatul`, `casa -> casa`, `cadou -> cadoul`

### Level 3: Cases
- Nominative and accusative
- Genitive and dative
- Basic case-driven sentence patterns
- Article and ending changes in simple contexts

### Level 4: Verbs
- Present tense conjugation patterns
- The four major verb group patterns
- Frequent everyday verbs
- Subject-verb agreement in realistic sentences

### Level 5: Pronouns and Core Tense Expansion
- Subject, direct object, and indirect object pronouns
- Reflexive constructions at a practical level
- Perfect compound tense in common contexts
- Near-future and standard future forms

### Level 6: Connected Everyday Communication
- Imperative forms
- Adverbs and comparison
- Time expressions and sequencing language
- Multi-clause sentences in daily-life contexts

### Level 7: Narrative and Functional B1 Grammar
- Imperfect vs perfect compound in guided contrast
- Motion, obligation, preference, and intention structures
- Relative clauses with common connectors
- Practical writing patterns for messages, plans, and descriptions

### Level 8: B1 to B2 Transition
- Conditional mood for requests, politeness, and hypotheticals
- More complex pronoun placement
- Expanded subordinate clauses for cause, purpose, and contrast
- Register awareness in common formal and informal situations

### Level 9: B2 Core Structures
- Passive and impersonal constructions where useful in modern Romanian
- Reported speech in controlled contexts
- Advanced connector use for argument and comparison
- Sustained paragraph-level comprehension and production

### Level 10: B2 Consolidation
- Mixed tense review in realistic discourse
- Nuanced case and article usage in longer contexts
- Error correction with multiple interacting grammar points
- Reading and writing tasks that require explanation, opinion, and justification

### B2 Exit Competencies
By the end of the B2 track, the learner should be able to:

- Understand the main ideas of moderately complex Romanian texts on concrete and abstract topics
- Follow and produce connected language across familiar work, travel, study, and personal contexts
- Explain opinions, compare options, and justify choices in multi-sentence responses
- Use the major high-frequency Romanian grammar patterns with reasonable control, even if occasional errors remain
- Handle integrated grammar tasks rather than only isolated sentence drills

## 7. Functional Requirements

### 7.1 Lesson Delivery
The application must:

- Present lessons in a hierarchical sequence
- Support AI-generated explanations and examples
- Store lesson history per user
- Allow review of previously completed lessons
- Support both single-skill lessons and integrated lessons for B1-B2 stages
- Tag each lesson with a CEFR target band such as A1, A2, B1, or B2

Each lesson should contain:

- `lesson_id`
- `topic`
- `level`
- `cefr_band`
- `difficulty`
- `explanation_text`
- `example_sentences`
- `key_rules`
- `quiz_questions`

### 7.1.1 Web-Based GUI
The application must provide a web-based GUI as a first-class interface.

The web GUI must:

- Show a pre-lesson level-introduction page that explains the grammar principles behind the topic before the learner starts a question set
- Show the current lesson explanation, worked examples, and key grammar rules
- Show quizzes and tests in an interactive form-based interface
- Show answer explanations after submission or review
- Show explicit explanations for wrong answers, not only the correct answer text
- Show overall learner progress across completed lessons and roadmap levels
- Show the learner's current CEFR estimate or competence band such as A1, A2, B1, or B2
- Show topic mastery or equivalent progress indicators for the current roadmap position
- Support review of past lesson results and recent quiz performance
- Be able to present placement-test sections and outcomes

The web GUI should be usable on a standard desktop browser first. Mobile responsiveness is desirable, but desktop browser support is the minimum requirement.

### 7.2 Question Types
The app must support at least these question types:

- Multiple choice
- English to Romanian translation
- Romanian to English translation
- Fill-in-the-blank
- Grammar error identification
- Sentence transformation
- Short guided writing
- Reading comprehension for multi-sentence passages
- Dialogue completion

Each question should include:

- Prompt
- Type
- Difficulty rating from 1 to 10
- Answer options when relevant
- Correct answer
- Explanation
- Grammar topic tags
- Optional hint
- Optional rubric data for open-response items

### 7.3 Adaptive Testing
The adaptive engine must modify lesson and quiz difficulty based on recent learner performance.

Rules:

- New users start at Level 1 unless they pass a placement test.
- If a user scores above 90 percent on a quiz, the next test should introduce more complex sentence structures and slightly harder vocabulary.
- If a user scores below 60 percent, the app must generate a review session focused on missed grammar rules before normal progression resumes.
- Scores from 60 to 90 percent should generally keep difficulty stable, with limited novelty.
- Topic advancement in the current MVP should require at least five completed question sets for the current topic, with the latest set scoring at least 80 percent and the average across all completed sets for that topic also at least 80 percent.
- Even after those score thresholds are met, the learner must still clear any pending previously incorrect answers for the topic before the next level unlocks.
- At B1 and B2 stages, adaptation must consider both grammar accuracy and ability to handle longer connected contexts.
- The system must not advance a user into B2-target content if prerequisite B1 grammar mastery remains below a configured threshold.

### 7.4 Review Sessions
A review session must:

- Focus on recently missed concepts
- Reuse the same grammar target with simpler examples
- Include hints or partial scaffolding
- Re-test mastery after review
- Continue contributing to the running per-topic average used for topic advancement decisions
- When score-based advancement would otherwise occur, switch to a remediation set containing every still-pending previously incorrect question for that topic

### 7.5 Placement Test
The system should support an initial placement test that:

- Samples multiple roadmap areas
- Estimates a starting difficulty
- Prevents advancing into topics with weak prerequisite mastery
- Estimates an initial CEFR band from A1 through B2

### 7.6 B2-Oriented Integrated Practice
For upper levels, the system must support:

- Passage-based reading tasks
- Contextual grammar in short dialogues and short paragraphs
- Guided opinion writing prompts
- Sentence linking and discourse-marker exercises
- Mixed-skill review sessions that combine tense, case, pronoun, and connector usage

## 8. AI Content Generation

### 8.1 Role of AI
AI is responsible for generating:

- Lesson explanations
- Example sentences
- Quiz questions
- Review session content
- Hints and answer explanations

AI is not trusted blindly. Every generated item must pass validation before being shown to users.

### 8.2 Prompt Inputs
The prompt construction layer must include:

- Current grammar topic
- Learner difficulty level
- User mastery data
- Frequently missed patterns
- Session goal such as lesson, quiz, review, or placement
- Constraints about realism and language level

### 8.3 Required Content Constraints
All prompts sent to the AI must enforce these constraints:

- Use common daily language
- Avoid archaic, poetic, or highly literary forms
- Avoid logically impossible or absurd sentences
- Stay within the learner's current topic boundaries
- Prefer realistic contexts such as meeting someone, shopping, family, travel, school, and work
- Explanations must be concise and clear for English speakers
- Questions must test one main concept at a time unless higher difficulty explicitly requires integration
- For B1-B2 content, permit multi-sentence contexts and integrated grammar only when prerequisite topics are already mastered
- B2 materials should include opinion, comparison, justification, and problem-solving contexts without becoming domain-specialist or academic

### 8.4 Sensible Question Standard
A question is considered sensible only if all of the following are true:

- The target grammar point is clearly identifiable
- The wording is natural enough for normal conversation or common study examples
- The answer is unambiguous
- Distractors are plausible but incorrect
- The explanation correctly describes why the answer is right
- Vocabulary difficulty matches the learner level
- For B1-B2 items, the passage or scenario remains coherent across multiple sentences
- Open-response prompts are specific enough to produce assessable answers

## 9. Content Validation Layer
The application must include a validation layer between the AI generator and the learner-facing content.

### 9.1 Structured Output
The AI should be required to return structured JSON. Suggested response structure:

```json
{
  "lesson_id": "uuid-or-generated-id",
  "topic": "definite_article",
  "level": 2,
  "difficulty": 3,
  "explanation_text": "Romanian attaches the definite article to the end of the noun.",
  "example_sentences": [
    {
      "romanian": "Baiatul este aici.",
      "english": "The boy is here."
    }
  ],
  "quiz_questions": [
    {
      "question_id": "q1",
      "type": "multiple_choice",
      "prompt": "Choose the correct form for 'the tree'.",
      "options": ["pom", "pomul", "pomi", "pomii"],
      "correct_answer": "pomul",
      "explanation": "The masculine singular definite form is 'pomul'.",
      "difficulty": 3,
      "tags": ["definite_article", "masculine_nouns"],
      "hint": "Look for the singular definite ending."
    }
  ]
}
```

### 9.2 Validation Rules
The validator must reject content if any of the following fail:

- JSON schema is invalid
- Required fields are missing
- `correct_answer` is not present in `options` for closed-form questions
- Question type and answer format do not match
- Difficulty is outside the allowed range
- Explanation is empty
- Topic tags do not match the requested lesson scope
- Duplicate options exist where uniqueness is required
- Sentences contain banned content or obviously irrelevant vocabulary

Current implementation baseline:

- Validation is performed inside the existing `AIService` flow before content is returned to callers
- Accepted content is normalized into the `Lesson` domain model and only then exposed as learner-safe output
- Rejected content triggers a retry with validation feedback embedded into the next prompt when retry budget remains
- If retries are exhausted, curated fallback templates plus archived offline AI questions are used for the supported A1-B2 roadmap topics
- Administrative CLI support can clear the archived offline bank entirely or seed it across the roadmap, targeting ten archived questions per topic by default
- Prompts that claim to be dialogue or reply tasks without including actual dialogue context are rejected

### 9.3 Optional Quality Checks
Where feasible, the validator should also perform:

- Basic Romanian diacritic normalization checks
- Length checks for explanations and prompts
- Duplicate question detection inside one lesson
- Lexical complexity limits by difficulty level
- CEFR-band consistency checks for vocabulary, sentence length, and task type
- Detection of uncontrolled topic jumps inside B2 passages

Rejected AI output should be retried with stricter prompting or fallback templates.

## 10. Adaptive Difficulty Model

### 10.1 Difficulty Range
- Minimum difficulty: 1
- Maximum difficulty: 10

The difficulty range should roughly align with roadmap and CEFR expectations:

- 1 to 2: early A1
- 3 to 4: late A1 to A2
- 5 to 6: solid A2 to early B1
- 7 to 8: B1
- 9 to 10: B2

### 10.2 Score-Based Adjustment Table

| Score Range | Difficulty Adjustment | AI Instruction Change |
| --- | --- | --- |
| 0% to 50% | Decrease by 1, minimum 1 | Use simpler vocabulary, shorter sentences, and explicit hints |
| 51% to 85% | Maintain | Reinforce current topic and add limited novelty |
| 86% to 100% | Increase by 1, maximum 10 | Use more complex syntax and reduced scaffolding |

### 10.3 Rolling Performance Logic
The core difficulty signal should use a rolling average of the last three quiz scores.

Suggested formula:

`next_difficulty = current_difficulty + (performance_factor * mastery_gap)`

Definitions:

- `mastery_gap = (recent_average_score - target_score)`
- `target_score = 80`
- `performance_factor = 0.1` as an initial damping factor

Implementation notes:

- Clamp final difficulty to the 1 to 10 range
- Use small increments to avoid erratic jumps
- If the latest score is below 60, trigger review regardless of the rolling average

## 11. System Architecture
The application should follow a modular architecture with clear separation between domain logic, AI integration, persistence, and interface layers.

Suggested Python package layout:

- `app/`
- `app/models/`
- `app/services/`
- `app/ai/`
- `app/validation/`
- `app/storage/`
- `app/controllers/`
- `app/ui/`
- `tests/`

### 11.1 Architectural Layers
- Model layer for user progress, lessons, questions, attempts, and mastery
- Service layer for adaptive logic and lesson orchestration
- AI layer for prompt building and provider integration
- Validation layer for schema and quality checks
- Storage layer for SQLite or file-based persistence
- UI layer that includes a web-based GUI for learner interaction and may also retain a CLI for development or administration tasks

## 12. Python Technical Requirements

### 12.1 Stack
- Language: Python 3.12+
- Packaging: `pyproject.toml`
- Data models: `dataclasses`
- Storage: SQLite for local persistence plus in-code seed content for roadmap and fallback data
- HTTP client: Python standard library `urllib`
- Web framework: current implementation uses a server-rendered WSGI app built on the Python standard library
- Testing: `pytest`

### 12.2 AI Provider Support
The design should allow at least one LLM provider at first, but the interface should be provider-agnostic.

Examples:
- OpenAI API
- Google Gemini API

The code should isolate provider-specific logic behind an `AIService` interface.

### 12.3 Assessment and Scoring Support
The implementation should support both closed-response and rubric-scored open-response tasks. For open-response items used in B1-B2 stages, the system may use AI-assisted scoring, but only with deterministic validation rules and human-readable scoring explanations.

## 13. Proposed Python Domain Model

### 13.1 UserProgress
Responsibility:
- Store current level
- Store XP
- Store recent quiz scores
- Store mastery by topic
- Store last lesson date
- Store current CEFR estimate
- Store reading, grammar, and writing support signals separately for upper levels

Suggested fields:
- `user_id`
- `current_level`
- `current_cefr_band`
- `current_difficulty`
- `total_xp`
- `mastery_matrix`
- `recent_scores`
- `skill_scores`
- `last_lesson_at`

### 13.2 Lesson
Responsibility:
- Represent one generated or curated lesson

Suggested fields:
- `lesson_id`
- `topic`
- `level`
- `cefr_band`
- `difficulty`
- `explanation_text`
- `example_sentences`
- `quiz_questions`

### 13.3 Question
Responsibility:
- Represent one assessment item

Suggested fields:
- `question_id`
- `prompt`
- `question_type`
- `options`
- `correct_answer`
- `explanation`
- `difficulty_rating`
- `cefr_band`
- `tags`
- `hint`
- `rubric`

### 13.4 DifficultyManager
Responsibility:
- Calculate next difficulty
- Decide whether to advance, hold, or review
- Select prompt constraints for the AI generator
- Gate progression into B2-target content using prerequisite mastery thresholds

### 13.5 ContentLibrary
Responsibility:
- Store curated Romanian grammar roadmap
- Provide canonical grammar descriptions
- Provide seed vocabulary and examples
- Support fallback generation when AI output fails
- Store CEFR-aligned topic groupings and prerequisite relationships

### 13.6 AIService
Responsibility:
- Build prompts
- Call the LLM provider
- Return structured content for validation

### 13.7 ContentValidator
Responsibility:
- Enforce schema rules
- Check question sensibility rules
- Reject or repair invalid outputs where possible

## 14. Persistence Model

### 14.1 Minimum Stored Entities
- Users
- Lessons served
- Quiz attempts
- Mastery by topic
- Skill scores
- Wordbank entries
- Archived offline AI-generated questions
- Pending incorrect-answer questions that still block advancement
- Offline-question-bank maintenance state such as total archived-question counts, which are surfaced through the `status` CLI output

### 14.2 Current SQLite Schema Shape

#### `users`
- `id` UUID primary key
- `current_level` integer
- `current_cefr_band` text
- `current_difficulty` integer
- `total_xp` integer
- `last_lesson_date` timestamp

#### `topic_mastery`
- `user_id` UUID
- `topic` text
- `proficiency_score` real

#### `lesson_history`
- `lesson_id` text
- `user_id` UUID
- `topic` text
- `level` integer
- `difficulty` integer
- `created_at` timestamp

#### `quiz_attempts`
- `attempt_id` UUID
- `user_id` UUID
- `lesson_id` text
- `score_percent` real
- `mistake_tags` text or JSON
- `created_at` timestamp

#### `skill_scores`
- `user_id` UUID
- `skill_name` text
- `score` real

#### `wordbank`
- `user_id` UUID
- `word` text
- `definition` text
- `topic` text
- `first_seen_at` timestamp

#### `offline_question_bank`
- `fingerprint` text primary key
- `topic` text
- `prompt` text
- `question_type` text
- `difficulty_rating` integer
- `cefr_band` text
- `correct_answer` text
- `explanation` text
- `tags` JSON text
- `options` JSON text
- `hint` text nullable
- `rubric` JSON text
- `provider_name` text nullable
- `model` text nullable
- `created_at` timestamp
- `last_seen_at` timestamp

#### `pending_incorrect_questions`
- `user_id` UUID
- `question_key` text
- `topic` text
- `question_type` text
- `prompt` text
- `correct_answer` text
- `payload` JSON text
- `first_incorrect_at` timestamp
- `last_seen_at` timestamp

## 15. AI Prompting Specification

### 15.1 System Prompt Requirements
The system prompt should establish:

- The app is teaching Romanian to English speakers
- The current grammar topic and level are mandatory constraints
- The target CEFR band is a mandatory constraint
- Generated content must be realistic and sensible
- Output must be valid JSON only
- Questions must be solvable from the lesson context and expected learner knowledge

### 15.2 Example Prompt Intent
Inputs:
- Topic: definite articles
- Difficulty: 3
- Recent misses: feminine noun endings
- Mode: review

Expected AI behavior:
- Focus on definite article suffixes
- Prefer simple household or daily-life vocabulary
- Include extra explanation around feminine patterns
- Avoid introducing unrelated case structures

## 16. Test Specification

### 16.1 Unit Tests
Unit tests must cover:

- Difficulty adjustment calculations
- Review trigger logic
- JSON schema validation
- Correct-answer-in-options checks
- Topic scope enforcement
- Mapping from user performance to prompt constraints
- CEFR gating and prerequisite checks
- Rubric scoring rules for guided writing items
- Web progress view-model calculations and CEFR display formatting where such logic exists outside templates
- Per-topic progression gating based on minimum completed set count plus latest-score and average-score thresholds
- Pre-lesson explanation content generation for level introductions where that logic exists outside templates

### 16.2 Integration Tests
Integration tests must cover:

- Full lesson generation flow from prompt builder to validator
- Retry behavior after invalid AI output
- Persistence of lesson and quiz results
- Persistence and later clearing of pending incorrect-answer questions
- Progress updates after completed quizzes
- Multi-set topic progression where the learner does not advance until the minimum set count and average-score requirements are both satisfied
- Stage 11 remediation gating where score-based progression is still blocked until prior incorrect answers are answered correctly
- Placement into the correct CEFR band up to B2
- Generation of integrated B1-B2 lessons without off-scope grammar leakage
- Web GUI rendering of level-introduction pages, lesson explanations, quiz/test screens, wrong-answer explanations, and learner progress summaries
- End-to-end display of current competence band and roadmap progression in the web interface

### 16.3 Prompt and Content Quality Tests
The system should include automated or semi-automated tests to verify:

- AI output conforms to schema
- Questions remain within requested topic scope
- Output does not exceed configured difficulty bounds
- Questions do not contain empty or contradictory explanations
- B2 passages remain coherent and appropriately challenging
- Open-response prompts are specific enough to score consistently

### 16.4 Acceptance Tests
The following acceptance criteria define a successful initial release:

1. A new user can start a lesson at Level 1 without manual setup.
2. The system can generate a Romanian grammar lesson and quiz in structured JSON.
3. Invalid AI output is rejected before reaching the user.
4. A score above 90 percent increases difficulty or complexity for the next lesson.
5. A score below 60 percent triggers a review session.
6. User progress is persisted locally.
7. At least the first four roadmap levels are supported.
8. A web GUI displays level introductions, lesson explanations, quizzes or tests, answer explanations including why wrong answers are wrong, overall progress, and the current language competence band.

### 16.5 Acceptance Tests for B2 Completion
The following criteria define successful upper-intermediate support:

1. The roadmap includes structured content from A1 through B2.
2. Placement testing can classify learners anywhere from A1 to B2.
3. The system can generate B1-B2 lessons with multi-sentence contexts and integrated grammar.
4. The system can deliver passage-based comprehension and guided writing tasks.
5. B2 progression is gated by prerequisite mastery rather than score spikes alone.
6. User records include CEFR progression checkpoints and skill-level signals.

## 17. Error Handling
The application must handle:

- AI provider timeouts
- Invalid or partial AI responses
- Persistence failures
- Missing user progress data

Fallback behavior should include:

- Retrying generation with a stricter prompt
- Falling back to template-based question generation for core grammar topics
- Logging validation failures for review

## 18. Security and Privacy
- API keys must be loaded from environment variables
- User data should remain local by default
- Logs must avoid storing secrets
- AI prompts should avoid sending unnecessary personally identifying information

## 19. Observability
The application should log:

- Prompt metadata without secrets
- Validation failures
- Difficulty changes
- Review triggers
- Lesson generation success and retry counts

## 20. Future Enhancements
- Desktop UI in addition to the required web GUI
- Audio pronunciation support
- Spaced repetition scheduling
- Curated human-authored lesson packs
- Teacher or admin content review tools
- Speaking assessment and pronunciation coaching for B1-B2
- Longer-form writing evaluation

## 21. Summary
Lumina Romana should be implemented as a Python application that teaches Romanian through adaptive grammar lessons and validated AI-generated content. The target scope is beginner through B2, which means the platform must support both foundational drills and upper-intermediate integrated language practice. The key product requirement is not just using AI, but using AI safely: every generated lesson and question must be structured, realistic, level-appropriate, CEFR-aware, and checked before it reaches the learner.
