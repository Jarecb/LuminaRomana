# Lumina Romana

Lumina Romana is a Python application for learning Romanian through adaptive grammar lessons and validated AI-generated quizzes. The project combines a structured Romanian learning roadmap with AI-assisted content generation, local user progress tracking, and deterministic difficulty scaling based on quiz performance.

The repository currently includes the Stage 0 foundation, Stage 1 persistence work, Stage 2 curriculum engine, and Stage 3 adaptive difficulty engine. The full product direction is defined in [spec.md](C:/Users/jarec/Dropbox/Python/LuminaRomana/spec.md), and the staged implementation roadmap is defined in [plan.md](C:/Users/jarec/Dropbox/Python/LuminaRomana/plan.md).

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
- Planned AI provider integration through an isolated service layer
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
There is no separate build step yet. This is currently a simple Python project with a package entrypoint, SQLite persistence bootstrap, and test coverage around the stage 1 core.

To prepare a local environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
pip install -e ".[dev]"
```

If editable install is not needed, you can run the entrypoint directly with Python.

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
- Prints a startup summary

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

## Development Notes
- The implementation should follow the requirements in [spec.md](C:/Users/jarec/Dropbox/Python/LuminaRomana/spec.md)
- AI-generated content must be validated before user display
- Adaptive quiz logic and review-session generation are core product requirements

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

AI integration, validation, and the learner-facing lesson loop remain for later stages.
