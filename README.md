# Lumina Romana

Lumina Romana is a Python application for learning Romanian through adaptive grammar lessons and validated AI-generated quizzes. The project combines a structured Romanian learning roadmap with AI-assisted content generation, local user progress tracking, deterministic difficulty scaling based on quiz performance, and a provider-backed AI integration layer.

The repository currently includes the Stage 0 foundation, Stage 1 persistence work, Stage 2 curriculum engine, Stage 3 adaptive difficulty engine, and Stage 4 AI integration layer. The full product direction is defined in [spec.md](C:/Users/jarec/Dropbox/Python/LuminaRomana/spec.md), and the staged implementation roadmap is defined in [plan.md](C:/Users/jarec/Dropbox/Python/LuminaRomana/plan.md).

## Index
- [Project Intent](#project-intent)
- [Tech Direction](#tech-direction)
- [Repository Layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Build](#build)
- [AI Installation](#ai-installation)
- [Run](#run)
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
Available run commands:

```powershell
python main.py
python -m app
lumina-romana
```

Expected current behavior:
- Loads base configuration from environment variables
- Configures application logging
- Initializes the local SQLite database
- Loads seeded roadmap metadata
- Builds the adaptive difficulty and AI service layers
- Prints a startup summary including AI provider status

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
- `LUMINA_ROMANA_AI_PROVIDER`: currently supports `openai`
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
- Stage 4 only establishes provider access and prompt construction; Stage 5 validation is still required before generated lessons should be considered learner-safe

## Development Notes
- The implementation should follow the requirements in [spec.md](C:/Users/jarec/Dropbox/Python/LuminaRomana/spec.md)
- AI-generated content must be validated before user display
- Adaptive quiz logic, review-session generation, and provider-backed prompt construction are core product requirements

## Current Status
This repository now has:

- Stage 0 foundation and startup wiring
- Stage 1 domain models for `UserProgress`, `Lesson`, `Question`, and `QuizAttempt`
- SQLite repositories for user progress, lesson history, quiz attempts, mastery tracking, and skill scores
- Stage 2 curriculum metadata for Levels 1 through 10 mapped across A1, A2, B1, and B2
- Prerequisite-aware topic selection and CEFR target-band lookup in `ContentLibrary`
- A placement-test blueprint that samples the roadmap from A1 through B2
- Stage 3 adaptive difficulty assessment with rolling score analysis, review-session planning, and prompt-constraint generation
- Explicit topic gating helpers that prevent access to blocked later-stage content, including B2 content with weak B1 prerequisites
- Stage 4 AI integration through `app.ai.AIService`, provider-backed JSON generation requests, prompt builders, transient retry handling, and metadata logging without secrets

Stage 5 validation and fallback generation, plus the learner-facing lesson loop, remain for later stages.
