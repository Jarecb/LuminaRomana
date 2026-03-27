# Lumina Romana Implementation Plan

## Index
- [Goal](#goal)
- [Delivery Principles](#delivery-principles)
- [Stage 0: Foundation and Project Setup](#stage-0-foundation-and-project-setup)
- [Stage 1: Core Domain Model and Local Persistence](#stage-1-core-domain-model-and-local-persistence)
- [Stage 2: Roadmap and Curriculum Engine](#stage-2-roadmap-and-curriculum-engine)
- [Stage 3: Adaptive Difficulty Engine](#stage-3-adaptive-difficulty-engine)
- [Stage 4: AI Integration Layer](#stage-4-ai-integration-layer)
- [Stage 5: Validation and Fallback Content](#stage-5-validation-and-fallback-content)
- [Stage 6: MVP Learning Loop](#stage-6-mvp-learning-loop)
- [Stage 7: B1 Expansion](#stage-7-b1-expansion)
- [Stage 8: B2 Learning Features](#stage-8-b2-learning-features)
- [Stage 9: Quality Hardening](#stage-9-quality-hardening)
- [Stage 10: Packaging and Deployment](#stage-10-packaging-and-deployment)
- [Recommended Build Order](#recommended-build-order)
- [Milestones](#milestones)
- [Immediate Next Steps](#immediate-next-steps)

## Goal
Implement the application in iterative stages so the project moves from a local scaffold to a working Romanian learning platform with adaptive AI-generated content and support up to CEFR B2.

## Delivery Principles
- Keep each stage independently testable
- Build deterministic validation before depending heavily on AI
- Deliver A1-A2 functionality first, then expand to B1-B2
- Build the browser-based learner experience after the curriculum and adaptive core are stable enough to support it

## Stage 0: Foundation and Project Setup
Status: completed on 2026-03-27.

Objective: turn the current scaffold into a maintainable Python project structure.

Deliverables:
- Create package layout under `app/`
- Replace placeholder `main.py` with a real application entrypoint
- Add dependency management in `pyproject.toml`
- Add base configuration loading
- Add logging setup
- Add `pytest` and test directories

Exit criteria:
- Project installs locally
- Application starts from a single command
- Test runner executes successfully

Implementation notes:
- Created the initial package layout under `app/` with placeholder modules for `ai`, `controllers`, `models`, `services`, `storage`, `ui`, and `validation`
- Replaced the PyCharm placeholder in `main.py` with a real entrypoint that delegates to `app.cli:main`
- Added `app.__main__` so the application can start with `python -m app`
- Added base runtime configuration in `app/config.py` using environment variables:
  `LUMINA_ROMANA_ENV`, `LUMINA_ROMANA_LOG_LEVEL`, and `LUMINA_ROMANA_DATA_DIR`
- Added centralized logging/bootstrap wiring in `app/logging_config.py` and `app/bootstrap.py`
- Updated `pyproject.toml` with package metadata, a console script, and optional dev dependencies for `pytest`
- Added initial smoke tests in `tests/test_cli.py` and `tests/test_config.py`
- Verified Stage 0 locally with:
  `.\.venv\Scripts\python.exe main.py`
  `.\.venv\Scripts\python.exe -m app`
  `.\.venv\Scripts\python.exe -m pytest`

Notes:
- The current CLI is intentionally minimal; it only proves startup, configuration, and logging paths
- Runtime code currently stays stdlib-only; external dependencies begin with test tooling
- No persistence, roadmap, adaptive logic, or AI integration is implemented yet

## Stage 1: Core Domain Model and Local Persistence
Status: completed on 2026-03-27.

Objective: build the non-AI core so lesson state and user progress are reliable.

Deliverables:
- Implement models for `UserProgress`, `Lesson`, `Question`, and `QuizAttempt`
- Implement SQLite persistence layer
- Add repository or storage interfaces
- Add seed topic metadata for the roadmap
- Add support for lesson history and mastery tracking

Exit criteria:
- User progress can be created, loaded, and updated
- Lessons and quiz attempts can be stored and retrieved
- Unit tests cover persistence and domain rules

Implementation notes:
- Added dataclass-based domain models in `app/models/domain.py` for `UserProgress`, `Lesson`, `Question`, and `QuizAttempt`
- Added roadmap seed metadata in `app/models/roadmap.py` and `app/services/roadmap.py` covering Levels 1 through 6 for the initial A1-A2 path
- Added SQLite schema bootstrap and repository implementations in `app/storage/sqlite.py` for:
  `users`, `topic_mastery`, `skill_scores`, `lesson_history`, and `quiz_attempts`
- Extended application bootstrap to create the runtime data directory, initialize the SQLite database, and expose repositories through the application container
- Expanded tests with domain, roadmap, and SQLite persistence coverage in:
  `tests/test_domain_models.py`
  `tests/test_roadmap.py`
  `tests/test_storage_sqlite.py`
- Updated CLI startup output to report the initialized database path and loaded seed topic count

Notes:
- The roadmap seed in Stage 1 is intentionally limited to the initial A1-A2 progression. Full curriculum graphing and next-topic selection remain Stage 2 work.
- Persistence is local-first and uses JSON serialization inside SQLite rows for lesson payloads while keeping mastery, skills, and attempts queryable in relational tables.

## Stage 2: Roadmap and Curriculum Engine
Status: completed on 2026-03-27.

Objective: encode the structured Romanian learning path and prerequisite graph.

Deliverables:
- Define roadmap data from A1 through B2
- Map internal levels to CEFR bands
- Add prerequisite relationships between topics
- Add lesson selection logic based on mastery and progression
- Add placement-test blueprint spanning A1 to B2

Exit criteria:
- The app can choose the next valid topic for a learner
- The system can report current CEFR target band
- Tests verify roadmap ordering and progression gating

Implementation notes:
- Expanded roadmap seed metadata in `app/models/roadmap.py` from the Stage 1 A1-A2 baseline to a full 10-level A1-B2 sequence aligned with the product spec
- Added a placement test blueprint model and seeded A1, A2, B1, and B2 placement sections with topic coverage and target difficulty ranges
- Extended `app/services/roadmap.py` so `ContentLibrary` now validates roadmap integrity and exposes:
  `placement_blueprint()`, `target_cefr_band()`, `available_topics()`, and `next_topic_for_user()`
- Implemented prerequisite-aware next-topic selection that returns blocking prerequisite topics before allowing later progression
- Expanded `tests/test_roadmap.py` to cover CEFR mapping, progression gating, available-topic calculation, and placement blueprint coverage
- Updated `README.md` to document the Stage 2 curriculum engine status and capabilities

Notes:
- Stage 2 focuses on deterministic curriculum decisions only. Score-based review logic and difficulty adaptation remain Stage 3 work.
- The placement blueprint currently defines coverage and intended difficulty ranges; question generation and scoring are still future-stage concerns.

## Stage 3: Adaptive Difficulty Engine
Status: completed on 2026-03-27.

Objective: implement score-based difficulty scaling and review logic.

Deliverables:
- Implement `DifficultyManager`
- Add rolling-score calculations
- Add review-session triggers
- Add gating rules so users cannot jump into B2 without prerequisites
- Add prompt-constraint generation from user performance

Exit criteria:
- Difficulty adjustments are deterministic and tested
- Review sessions are triggered correctly
- CEFR and prerequisite gating work under edge cases

Implementation notes:
- Added `app/services/difficulty.py` with a `DifficultyManager` that:
  calculates rolling averages from the last three quiz scores, determines the next difficulty deterministically, and classifies the next session as `advance`, `hold`, or `review`
- Implemented review-session planning that prioritizes prerequisite gaps and common recent mistake tags for targeted re-checks
- Extended `ContentLibrary` with explicit topic-unlock and blocking-topic helpers so later-stage topic access, including B2, can be validated against prerequisite mastery
- Wired the adaptive service into application bootstrap so it is available through the runtime container
- Added Stage 3 coverage in:
  `tests/test_difficulty.py`
  `tests/test_roadmap.py`
- Verified Stage 3 locally with:
  `.\.venv\Scripts\python.exe -m pytest`

Notes:
- Difficulty changes use the spec's rolling-average approach with bounded one-step adjustments and an immediate review trigger for latest scores below 60 percent
- Prompt constraints are now generated deterministically from learner performance, CEFR state, and prerequisite blocking so the later AI layer can consume stable adaptation signals

## Stage 4: AI Integration Layer
Status: completed on 2026-03-27.

Objective: connect the system to an LLM provider behind a stable interface.

Deliverables:
- Implement provider-agnostic `AIService`
- Add prompt-builder components
- Add environment-based API key configuration
- Add request and response logging without secrets
- Add retry behavior for transient failures

Exit criteria:
- The app can request lesson content from one provider
- Prompt construction uses learner state, topic, difficulty, and CEFR band
- Failure paths are logged and recoverable

Implementation notes:
- Added a provider-agnostic AI layer under `app/ai/` with:
  `AIService`, prompt-builder components, provider response types, and AI-specific error classes
- Implemented an OpenAI-compatible chat-completions provider behind the stable provider interface, plus a disabled provider used when no API configuration is present
- Added prompt construction that combines:
  roadmap topic metadata, learner CEFR state, adaptive difficulty assessment, focus tags, blocked-topic gating, and session-goal constraints
- Extended `Settings` with environment-based AI configuration for:
  `LUMINA_ROMANA_AI_ENABLED`, `LUMINA_ROMANA_AI_PROVIDER`, `LUMINA_ROMANA_AI_MODEL`, `LUMINA_ROMANA_AI_API_KEY`, `LUMINA_ROMANA_AI_BASE_URL`, `LUMINA_ROMANA_AI_TIMEOUT_SECONDS`, and `LUMINA_ROMANA_AI_MAX_RETRIES`
- Wired the AI service into application bootstrap and surfaced provider status in CLI startup output
- Added retry handling for transient provider and network failures, with request and response logging that records metadata and token usage without logging secrets
- Added Stage 4 coverage in:
  `tests/test_ai.py`
  `tests/test_config.py`
  `tests/test_cli.py`
- Verified Stage 4 locally with:
  `.\.venv\Scripts\python.exe -m pytest`

Notes:
- AI integration is now available when an API key is configured, but Stage 5 validation and fallback logic is still required before generated content should be treated as learner-safe
- The first provider implementation targets the OpenAI chat completions API; the service boundary is intentionally provider-agnostic so additional providers can be added later

## Stage 5: Validation and Fallback Content
Status: completed on 2026-03-27.

Objective: ensure AI output is safe enough to use.

Deliverables:
- Implement JSON schema validation
- Validate question structure and answer consistency
- Add sensibility checks and topic-scope checks
- Add fallback template generation for core grammar topics
- Add content rejection and retry workflow

Exit criteria:
- Invalid AI output never reaches the learner
- Core A1-A2 topics still work when AI output fails
- Integration tests cover retry and fallback behavior

Implementation notes:
- Added a real validation layer under `app/validation/` with `ContentValidator`, structured validation issues, and payload-to-domain normalization so AI output must validate into a `Lesson` before it can be used
- Implemented deterministic schema and sensibility checks for:
  required fields, CEFR and level consistency, question structure, answer-option consistency, duplicate prompts, off-scope topic tags, and banned absurd vocabulary
- Extended `AIService` so generation now:
  validates provider JSON, retries with validation feedback in stricter prompts when output is rejected, and falls back to deterministic template lessons for core A1-A2 topics when AI generation remains unusable
- Extended `ContentLibrary` with curated fallback lesson templates for Levels 1 through 6 so beginner and lower-intermediate topics remain available without AI
- Added Stage 5 coverage in:
  `tests/test_validation.py`
  `tests/test_ai.py`
- Verified Stage 5 locally with:
  `.\.venv\Scripts\python.exe -m pytest`

Notes:
- Stage 5 now sits directly on top of the existing Stage 4 AI layer rather than creating a separate content-generation path
- Unsupported fallback topics still surface generation failures explicitly, which keeps later B1-B2 lesson safety dependent on validated AI output until curated fallbacks are added

## Stage 6: MVP Learning Loop
Objective: deliver an end-to-end A1-A2 product loop with a web-based learner interface.

Deliverables:
- Lesson delivery flow
- Quiz flow
- Review-session flow
- Web-based GUI for lessons, tests, explanations, and progress display
- CLI retained only for development, diagnostics, or admin workflows
- Local progress resume

Exit criteria:
- A new learner can start, complete lessons, take quizzes, and receive adaptive follow-up
- Progress persists across sessions
- The web GUI shows current lesson explanations, test items, answer explanations, overall progress, and the learner's current CEFR competence band
- Acceptance criteria for the initial MVP are met

Implementation guidance:
- Reuse the existing domain, storage, and curriculum services rather than duplicating logic in the UI layer
- Prefer a thin web layer that renders learner-facing views from application services and persistence-backed state
- Include integration tests for browser-facing lesson, quiz, explanation, and progress pages

## Stage 7: B1 Expansion
Objective: extend beyond beginner grammar into connected communication and narrative use.

Deliverables:
- Add B1 grammar topics and vocabulary constraints
- Add multi-sentence lesson examples
- Add sentence transformation and dialogue completion tasks
- Add intermediate placement support
- Expand mastery tracking for integrated grammar

Exit criteria:
- The app can serve B1 lessons with coherent multi-step grammar tasks
- Placement can classify at least through B1
- Tests verify topic containment and increasing complexity

## Stage 8: B2 Learning Features
Objective: support upper-intermediate learning rather than only sentence-level drills.

Deliverables:
- Add B2 roadmap topics
- Add passage-based reading tasks
- Add guided writing prompts with rubrics
- Add discourse-marker and argumentation tasks
- Add skill-level tracking for grammar, reading, and writing support
- Extend the web GUI to present integrated B2 reading and writing workflows clearly

Exit criteria:
- The system can generate and validate B2-target lessons
- The learner can complete integrated comprehension and writing tasks
- B2 progression depends on sustained mastery, not isolated quiz spikes

## Stage 9: Quality Hardening
Objective: reduce regressions and improve trustworthiness before wider use.

Deliverables:
- Expand unit and integration test coverage
- Add prompt regression fixtures
- Add content-quality sampling workflow
- Add metrics for validation failures and retry rates
- Tune fallback logic and difficulty parameters

Exit criteria:
- Core flows are covered by automated tests
- AI generation quality is measurable
- Validation and retry behavior are stable under repeated runs

## Stage 10: Packaging and Deployment
Objective: make the application easy to run outside the development environment.

Deliverables:
- Finalize CLI commands
- Finalize web application startup and deployment commands
- Add environment example documentation
- Add packaging instructions
- Add optional executable packaging or containerization for the web app
- Document local deployment and update flow for both CLI support tooling and the web GUI

Exit criteria:
- A new user can install and run the app from documentation alone, including the web GUI
- Configuration for AI provider keys is documented
- The deploy path is repeatable

## Recommended Build Order
1. Stage 0
2. Stage 1
3. Stage 2
4. Stage 3
5. Stage 5
6. Stage 4
7. Stage 6
8. Stage 7
9. Stage 8
10. Stage 9
11. Stage 10

Validation is placed before heavy AI reliance on purpose. Without that sequencing, the project will generate content faster than it can trust it.

## Milestones
- Milestone 1: project foundation plus persistence
- Milestone 2: A1-A2 adaptive MVP with web GUI
- Milestone 3: B1 expansion
- Milestone 4: B2 completion
- Milestone 5: packaging and deployment readiness

## Immediate Next Steps
1. Deliver Stage 6 with a web-based GUI that shows lessons, tests, explanations, learner progress, and current CEFR competence band.
2. Extend the AI layer to support lesson orchestration flows on top of the new validation and fallback gate.
3. Add end-to-end generation tests that cover bootstrap, provider calls, validation, fallback behavior, and persistence together.
4. Expand curated fallback coverage if B1-B2 offline or provider-disabled operation becomes a product requirement.
