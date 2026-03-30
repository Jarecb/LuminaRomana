# Lumina Romana

Lumina Romana is a Python application for learning Romanian through adaptive grammar lessons and validated AI-generated quizzes. The project combines a structured Romanian learning roadmap with AI-assisted content generation, local user progress tracking, deterministic difficulty scaling based on quiz performance, a provider-backed AI integration layer, a validation-plus-fallback safety gate in front of learner-facing content, and a browser-based Stage 8 learning loop with initial B2 support.

The repository currently includes the Stage 0 foundation, Stage 1 persistence work, Stage 2 curriculum engine, Stage 3 adaptive difficulty engine, Stage 4 AI integration layer, Stage 5 validation and fallback content, Stage 6 MVP lesson delivery in a web UI, Stage 7 B1 expansion, Stage 8 B2 learning features, and Stage 9 quality hardening. The full product direction is defined in [spec.md](C:/Users/jarec/Dropbox/Python/LuminaRomana/spec.md), and the staged implementation roadmap is defined in [plan.md](C:/Users/jarec/Dropbox/Python/LuminaRomana/plan.md).

## Index
- [Project Intent](#project-intent)
- [Tech Direction](#tech-direction)
- [Repository Layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Build](#build)
- [AI Installation](#ai-installation)
- [Run](#run)
- [Web UI](#web-ui)
- [Test](#test)
- [Deploy](#deploy)
- [Configuration](#configuration)
- [AI Configuration](#ai-configuration)
- [Development Notes](#development-notes)
- [Current Status](#current-status)

## Project Intent
- Teach Romanian grammar progressively, starting from phonetics and basic verb usage
- Generate lessons, examples, and quizzes with AI
- Validate AI output so questions remain sensible and on-topic
- Adapt lesson difficulty using recent learner performance
- Persist user progress locally

## Tech Direction
- Python 3.12+
- `pyproject.toml`-based project setup
- Local persistence with SQLite
- Dataclass-based domain models for learner progress, lessons, questions, and quiz attempts
- Seeded roadmap metadata and curriculum selection from A1 through B2
- Provider-agnostic AI integration with prompt builders, retry handling, and an OpenAI-compatible provider implementation
- Deterministic lesson validation, scope checking, and fallback lesson generation for core A1-A2, B1, and initial B2 topics
- A server-rendered WSGI web interface for lesson delivery, quizzes, answer explanations, and progress tracking
- Automated testing with `pytest`

## Repository Layout
- [app/](C:/Users/jarec/Dropbox/Python/LuminaRomana/app): application package with models, services, AI, validation, storage, controllers, and UI layers
- [main.py](C:/Users/jarec/Dropbox/Python/LuminaRomana/main.py): top-level entrypoint
- [pyproject.toml](C:/Users/jarec/Dropbox/Python/LuminaRomana/pyproject.toml): package metadata and test tooling
- [spec.md](C:/Users/jarec/Dropbox/Python/LuminaRomana/spec.md): full product and test specification
- [plan.md](C:/Users/jarec/Dropbox/Python/LuminaRomana/plan.md): staged implementation plan

## Prerequisites
- Python 3.12 or newer
- PowerShell on Windows, or an equivalent shell

## Build
There is no separate build step yet. This is currently a simple Python project with a package entrypoint, SQLite persistence bootstrap, adaptive services, and tested AI integration plumbing.

To prepare a local environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
pip install -e ".[dev]"
```

If editable install is not needed, you can run the entrypoint directly with Python.

## AI Installation
The current AI integration uses the Python standard library for HTTP calls, so there is no extra package to install for the built-in OpenAI-compatible provider.

Standard setup:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
pip install -e ".[dev]"
```

If you want to use AI generation, you only need to provide environment configuration. No additional SDK install is required for the current implementation.

## Run
The CLI currently supports these commands.

From a local checkout, the most reliable form is:

```powershell
python main.py
python main.py status
python main.py serve
python main.py reset-progress
python main.py set-progress --band B1
python main.py set-progress --level 9
python main.py sample-content --topics romanian_basics b2_core_structures
```

If you installed the package with `pip install -e .`, the same commands are also available as:

```powershell
lumina-romana
lumina-romana status
lumina-romana serve
lumina-romana reset-progress
lumina-romana set-progress --band B1
lumina-romana set-progress --level 9
lumina-romana sample-content --topics romanian_basics b2_core_structures
```

Command summary:
- `status`: loads configuration, initializes the database and services, and prints the current runtime summary. This is also the default command when no subcommand is given.
- `serve`: starts the local web server for the browser-based learner interface.
- `reset-progress`: clears the default learner's saved progress and recreates a fresh Level 1 / A1 / difficulty 1 state for testing.
- `set-progress`: jumps the default learner to a testing position by CEFR band or exact roadmap level, clearing saved lesson history, quiz attempts, and wordbank state first so the next session starts cleanly from that point.
- `sample-content`: runs the Stage 9 content-quality sampling workflow across selected roadmap topics and prints source, question-type, and AI-metrics summaries for each sample.

Examples:

```powershell
python main.py status
python main.py serve
python main.py reset-progress
python main.py set-progress --band A2
python main.py set-progress --band B2
python main.py set-progress --level 8
python main.py set-progress --level 9 --difficulty 10
python main.py sample-content --topics romanian_basics narrative_b1_grammar b2_core_structures
```

`set-progress` targets:

- `--band A1` jumps to Level 1
- `--band A2` jumps to Level 5
- `--band B1` jumps to Level 7
- `--band B2` jumps to Level 9
- `--level N` jumps to the exact roadmap level from 1 through 10
- `--difficulty N` optionally overrides the default testing difficulty for that jump

If you want to replay an already-completed level without changing stored progress, open the browser app, go to `/progress`, and use the `Redo level` button next to any level up to your current position. That launches a practice replay and leaves the learner's saved mastery and current roadmap position unchanged after submission.

The `status` command now also reports the current in-process AI-generation metrics snapshot, and `sample-content` prints the validation-failure, retry, and fallback deltas produced by the sample run.

## Web UI
Stage 6 introduces a browser-based learner loop aligned to the MVP requirements in [spec.md](C:/Users/jarec/Dropbox/Python/LuminaRomana/spec.md).

Start the web interface with:

```powershell
python main.py serve
```

Default local address:

```text
http://127.0.0.1:8000
```

Current browser flow:
- Dashboard with current CEFR estimate, recommended action, recent lessons, recent quiz scores, roadmap progress, and the current level-average summary
- Level introduction page before each new roadmap topic, with descriptive explanations of the grammar principles being taught
- Lesson page with explanation text, worked examples, key rules, and an interactive question-set form
- Result page with per-question answer explanations, explicit wrong-answer explanations, and the running level average after submission
- Progress page with current level, difficulty, XP, recent scores, mastery summary, and current topic-average information
- Automatic resume of an unfinished lesson
- Review-session generation after scores below 60 percent
- Topic progression gated by at least five completed question sets, 80 percent or higher on the current set, and an 80 percent or higher average across all sets for the current topic
- Initial B1-capable sessions with multi-sentence examples, sentence transformation tasks, and dialogue completion tasks when the learner reaches Levels 7 to 8
- Initial B2-capable sessions with reading comprehension, guided writing, rubric display, and paragraph-style prompts when the learner reaches Levels 9 to 10
- A `Redo level` action on the progress screen so completed levels can be replayed for testing without changing stored mastery or the learner's current roadmap position

The web layer is intentionally thin and reuses the existing persistence, roadmap, difficulty, AI, and validation services instead of duplicating business logic.

## Test
Run the current test suite with:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Deploy
There is no deployment pipeline yet.

Planned deployment approach:
- Local-first development and usage
- Environment-based configuration for AI API keys
- Optional packaging as a CLI application
- Future deployment targets may include a small web service or desktop distribution after the core learning engine is implemented

## Configuration
The scaffold supports these environment variables:

- `LUMINA_ROMANA_ENV`
- `LUMINA_ROMANA_LOG_LEVEL`
- `LUMINA_ROMANA_DATA_DIR`
- `LUMINA_ROMANA_DB_PATH`
- `LUMINA_ROMANA_AI_ENABLED`
- `LUMINA_ROMANA_AI_PROVIDER`
- `LUMINA_ROMANA_AI_MODEL`
- `LUMINA_ROMANA_AI_API_KEY`
- `LUMINA_ROMANA_AI_BASE_URL`
- `LUMINA_ROMANA_AI_TIMEOUT_SECONDS`
- `LUMINA_ROMANA_AI_MAX_RETRIES`
- `LUMINA_ROMANA_WEB_HOST`
- `LUMINA_ROMANA_WEB_PORT`

By default the app starts with AI disabled unless a key is configured. The current provider implementation targets the OpenAI chat completions API.

## AI Configuration
The built-in provider expects an OpenAI-compatible chat completions endpoint.

Minimum configuration in PowerShell:

```powershell
$env:LUMINA_ROMANA_AI_ENABLED = "true"
$env:LUMINA_ROMANA_AI_PROVIDER = "openai"
$env:LUMINA_ROMANA_AI_MODEL = "gpt-4.1-mini"
$env:LUMINA_ROMANA_AI_API_KEY = "your-api-key"
```

Optional overrides:

```powershell
$env:LUMINA_ROMANA_AI_BASE_URL = "https://api.openai.com/v1"
$env:LUMINA_ROMANA_AI_TIMEOUT_SECONDS = "30"
$env:LUMINA_ROMANA_AI_MAX_RETRIES = "2"
```

Variable behavior:

- `LUMINA_ROMANA_AI_ENABLED`: enables or disables AI calls explicitly
- `LUMINA_ROMANA_AI_PROVIDER`: currently supports `openai` and `gemini`
- `LUMINA_ROMANA_AI_MODEL`: model name sent to the provider
- `LUMINA_ROMANA_AI_API_KEY`: bearer token for the AI provider
- `LUMINA_ROMANA_AI_BASE_URL`: base URL for OpenAI or any compatible endpoint
- `LUMINA_ROMANA_AI_TIMEOUT_SECONDS`: request timeout per provider call
- `LUMINA_ROMANA_AI_MAX_RETRIES`: retry count for transient failures; total attempts are retries plus the initial request

Verification:

```powershell
python main.py
```

Startup output should include a line similar to:

```text
AI provider: openai (gpt-4.1-mini, configured=True)
```

If configuration is missing or disabled, startup will report:

```text
AI provider: disabled (..., configured=False)
```

Notes:

- API keys are loaded from environment variables only
- Request and response metadata are logged without logging the API key
- AI-generated lessons are now validated before they are returned from `AIService`
- If AI output is invalid or the provider is unavailable, supported beginner, B1, and initial B2 topics fall back to deterministic template lessons
- Later-stage enhancements beyond the current B2 set still depend on validated AI output or future curated expansions

## Development Notes
- The implementation should follow the requirements in [spec.md](C:/Users/jarec/Dropbox/Python/LuminaRomana/spec.md)
- AI-generated content must be validated before user display
- Adaptive quiz logic, review-session generation, provider-backed prompt construction, and validation-backed fallback generation are core product requirements

## Current Status
This repository now has:

- Stage 0 foundation and startup wiring
- Stage 1 domain models for `UserProgress`, `Lesson`, `Question`, and `QuizAttempt`
- SQLite repositories for user progress, lesson history, quiz attempts, mastery tracking, and skill scores
- Stage 2 curriculum metadata for Levels 1 through 10 mapped across A1, A2, B1, and B2
- Prerequisite-aware topic selection and CEFR target-band lookup in `ContentLibrary`
- A placement-test blueprint that samples the roadmap from A1 through B2
- Placement evaluation logic that can classify through B2 and recommend a starting topic
- Stage 3 adaptive difficulty assessment with rolling score analysis, review-session planning, and prompt-constraint generation
- Explicit topic gating helpers that prevent access to blocked later-stage content, including B2 content with weak B1 prerequisites
- Stage 4 AI integration through `app.ai.AIService`, provider-backed JSON generation requests, prompt builders, transient retry handling, and metadata logging without secrets
- Stage 5 validation through `app.validation.ContentValidator`, including schema-like checks, scope enforcement, answer consistency checks, and sensibility filtering
- Stage 5, Stage 7, and Stage 8 fallback lesson generation in `ContentLibrary` for the core A1-A2 roadmap topics plus initial B1 and B2 topics when validated AI output is unavailable
- Stage 6 learner-session orchestration in `app.services.learning`, including level introductions, lesson resume, multi-set topic scoring, progress updates, mastery advancement, review-session routing, and CLI reset support
- Stage 7 intermediate task support, including sentence transformation, dialogue completion, B1 multi-sentence examples, and integrated grammar skill tracking
- Stage 8 B2 task support, including reading comprehension, guided writing with rubrics, discourse-marker work, paragraph-style prompt rendering, and visible reading/writing skill signals in the web UI
- Stage 9 quality hardening through AI-generation metrics, prompt regression fixtures, the content-quality sampling workflow, and broader retry/fallback regression coverage
- Stage 6 browser-facing lesson, level-intro, quiz, explanation, and progress screens in `app.ui.web`
- Integration and regression tests covering browser flow, persistence-backed progress updates, prompt regressions, and AI retry or fallback behavior
