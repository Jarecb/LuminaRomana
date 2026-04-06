# Lumina Romana Deployment Guide

## Overview
Lumina Romana is a local-first Python application with a browser UI, a small CLI, SQLite persistence, optional AI-backed lesson generation, and an offline-only server mode for fallback-only operation.

The supported Stage 10 deployment paths are:

- local source checkout with `python main.py ...`
- editable install with the `lumina-romana` console script
- built wheel install
- optional Docker container for the web UI

All persistent learner data lives in the configured data directory. By default that is `data/`, which contains `lumina_romana.db`.

## Local Source Run
### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
pip install -e ".[dev]"
```

### 2. Configure AI in `run_server.bat`
Edit `run_server.bat` and set:

- `LUMINA_ROMANA_AI_ENABLED`
- `LUMINA_ROMANA_AI_PROVIDER`
- `LUMINA_ROMANA_AI_MODEL`
- `LUMINA_ROMANA_AI_API_KEY`

Provider values:

- `gemini` or `google` for Gemini
- `copilot` for GitHub Copilot or another OpenAI-compatible endpoint
- `openai` for standard OpenAI-compatible chat completions

### 3. Start the web app

```powershell
.\run_server.bat
```

Or directly:

```powershell
python main.py serve
```

Offline-only browser startup:

```powershell
.\run_server.bat --offline
python main.py serve --offline
python main.py -o
```

When started in offline-only mode, the server process never calls an AI provider and does not require AI credentials for that run.

`run_server.bat` can also forward CLI commands while keeping the same AI configuration loaded from the batch file:

```powershell
.\run_server.bat status
.\run_server.bat seed-offline-questions
.\run_server.bat clear-offline-questions
```

## CLI Commands
The CLI is intended for local administration, diagnostics, testing, and offline-question-bank maintenance.

Command reference:

- `status`
  Shows the current runtime environment, database path, roadmap topic count, offline-question-bank size, and AI provider status.
- `serve`
  Starts the browser UI.
- `serve -o`
  Starts the browser UI in offline-only mode. The aliases `-offline` and `--offline` are also accepted.
- `reset-progress`
  Resets the default learner profile back to the starting position and clears its saved progress state.
- `set-progress --band <A1|A2|B1|B2>`
  Moves the default learner to the first roadmap level of the selected CEFR band.
- `set-progress --level <N> [--difficulty <N>]`
  Moves the default learner to an exact roadmap level for testing.
- `sample-content [--topics ...] [--question-count N] [--goal lesson|review|practice]`
  Runs the content-quality sampling workflow and reports AI versus fallback generation behavior.
- `clear-offline-questions`
  Deletes the archived offline question bank only. It does not reset learner progress.
- `seed-offline-questions [--topics ...] [--question-count N] [--goal lesson|review|practice]`
  Tries to top up the offline question bank. With no `--topics`, it processes the full A1-B2 roadmap and targets a minimum archived-question count per topic.

Command selection guidance:

- Use `python main.py ...` for normal local CLI work when AI configuration is already present in your shell environment.
- Use `.\run_server.bat ...` when you want the command to inherit the AI settings defined at the top of `run_server.bat`.

Examples:

```powershell
python main.py status
python main.py serve --offline
python main.py set-progress --band B1
python main.py sample-content --topics romanian_basics b2_core_structures
python main.py clear-offline-questions
python main.py seed-offline-questions
python main.py seed-offline-questions --topics romanian_basics b2_core_structures --question-count 10
```

If installed with `pip install -e .` or from a wheel, you can also run:

```powershell
lumina-romana status
lumina-romana serve
lumina-romana serve --offline
```

Offline question bank maintenance notes:

- `clear-offline-questions` deletes all archived offline questions without resetting learner progress.
- `seed-offline-questions` targets the full A1-B2 roadmap by default and tries to top each roadmap topic up to the requested minimum archived-question count.
- If AI is unavailable, the seed command still archives any unique deterministic fallback questions it can generate and reports any remaining shortfall.
- If your AI settings live in `run_server.bat`, run the CLI commands through `.\run_server.bat ...` so those environment variables are applied to the same process.

## Build a Wheel
Build artifacts can be created with the standard Python build backend:

```powershell
python -m pip install --upgrade build
python -m build
```

This creates `dist/` artifacts that can be installed elsewhere with:

```powershell
pip install dist\lumina_romana-0.1.0-py3-none-any.whl
```

## Docker Runtime
### Build

```powershell
docker build -t lumina-romana .
```

### Run

Gemini example:

```powershell
docker run --rm -p 8000:8000 ^
  -e LUMINA_ROMANA_AI_ENABLED=true ^
  -e LUMINA_ROMANA_AI_PROVIDER=gemini ^
  -e LUMINA_ROMANA_AI_MODEL=gemini-2.5-flash ^
  -e LUMINA_ROMANA_AI_API_KEY=your-key ^
  -v ${PWD}\data:/app/data ^
  lumina-romana
```

Offline-only example:

```powershell
docker run --rm -p 8000:8000 ^
  -e LUMINA_ROMANA_AI_OFFLINE_ONLY=true ^
  -v ${PWD}\data:/app/data ^
  lumina-romana python main.py serve --offline
```

Copilot/OpenAI-compatible example:

```powershell
docker run --rm -p 8000:8000 ^
  -e LUMINA_ROMANA_AI_ENABLED=true ^
  -e LUMINA_ROMANA_AI_PROVIDER=copilot ^
  -e LUMINA_ROMANA_AI_MODEL=gpt-4.1 ^
  -e LUMINA_ROMANA_AI_API_KEY=your-key ^
  -e LUMINA_ROMANA_AI_BASE_URL=https://your-openai-compatible-endpoint/v1 ^
  -v ${PWD}\data:/app/data ^
  lumina-romana
```

## Data and Backup
The learner database includes:

- user progress
- lesson history
- quiz attempts
- wordbank entries
- archived offline AI-generated questions

Use `python main.py status` to confirm the current offline question bank size after seeding or clearing.
Use `python main.py serve --offline` when you need the web app to stay strictly on fallback and archived offline content.

Back up the configured data directory to preserve all learner state.

## Update Flow
### Source checkout

```powershell
git pull
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python -m pytest -q
```

### Wheel deployment

Rebuild on the source machine, copy the new wheel, and reinstall it:

```powershell
pip install --upgrade dist\lumina_romana-0.1.0-py3-none-any.whl
```

### Docker deployment

```powershell
docker build -t lumina-romana .
docker stop lumina-romana
docker rm lumina-romana
```

Then rerun `docker run ...` with the same mounted data directory.
