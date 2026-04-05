# Lumina Romana

Lumina Romana is a local-first Romanian grammar trainer with:

- a browser-based learning loop
- adaptive difficulty and review routing
- validated AI lesson generation
- deterministic fallback lessons
- SQLite-backed learner progress, lesson history, wordbank, and archived offline question storage

The application currently supports the full staged implementation through Stage 11 in `plan.md`: A1 through B2 roadmap coverage, Gemini and OpenAI-compatible providers including Copilot-style endpoints, browser delivery, incorrect-answer mastery gating, quality hardening, and repeatable packaging or deployment workflows.

## What the App Does
- Serves Romanian grammar lessons and question sets in a local web UI
- Tracks progress, mastery, recent scores, CEFR estimate, and skill signals
- Persists incorrectly answered questions and forces mastery-gate remediation before level advancement
- Uses AI for lesson generation when configured
- Falls back to deterministic local content when AI is unavailable or invalid
- Stores validated AI-generated questions into the offline question bank so local fallback content expands over time
- Supports CLI maintenance of the offline question bank, including clearing it and seeding it across the full A1-B2 roadmap
- Supports wordbank browsing and practice replays
- Provides developer CLI commands for status, reset, test positioning, and content sampling

## Current Learning Flow
The main browser entrypoint is the dashboard button `Start or resume session`.

Current behavior:

- if an unfinished lesson exists, it resumes it
- otherwise it generates the next lesson immediately through the AI-plus-validation pipeline
- if the learner has met the normal score thresholds for a level but still has unresolved incorrect answers from non-practice attempts, it serves a remediation set containing those exact pending questions before allowing advancement
- if AI is disabled, unavailable, or rejected by validation, it falls back to local question sets
- no lesson is allowed to contain the same question more than once

Supporting pages:

- dashboard
- lesson view with worked examples and key rules
- result page with answer explanations and explicit wrong-answer feedback
- progress view with roadmap state and practice replay
- wordbank view
- level intro and revision pages, still available by route

## Installation
### Local editable install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
pip install -e ".[dev]"
```

### Build a wheel

```powershell
python -m pip install --upgrade build
python -m build
```

Install the built wheel with:

```powershell
pip install dist\lumina_romana-0.1.0-py3-none-any.whl
```

## Run
### Browser UI
The Windows-first startup path is `run_server.bat`.

Edit the AI settings at the top of `run_server.bat`, then run:

```powershell
.\run_server.bat
```

The script:

- sets the app and AI environment variables
- prefers `.venv\Scripts\python.exe` when available
- launches `python main.py <command>` with `serve` as the default

Direct startup also works:

```powershell
python main.py serve
```

Default address:

```text
http://127.0.0.1:8000
```

If you want CLI commands to use the AI settings from `run_server.bat`, run them through the batch file as well:

```powershell
.\run_server.bat status
.\run_server.bat seed-offline-questions
.\run_server.bat seed-offline-questions --topics romanian_basics --question-count 100
```

### CLI
The CLI is mainly for diagnostics, testing, and offline-content maintenance. Use `python main.py ...` for generic local commands, or `.\run_server.bat ...` when you want the AI settings defined in `run_server.bat` to apply to the same process.

Command reference:

- `status`: prints the current environment, database path, topic count, offline-question-bank size, and active AI provider status.
- `serve`: starts the browser UI on the configured host and port.
- `reset-progress`: resets the default learner profile back to Level 1, A1, difficulty 1, and clears its stored progress history.
- `set-progress --band <A1|A2|B1|B2>`: jumps the default learner to the first roadmap level for that CEFR band.
- `set-progress --level <N> [--difficulty <N>]`: jumps the default learner to an exact roadmap level, optionally forcing a testing difficulty.
- `sample-content [--topics ...] [--question-count N] [--goal lesson|review|practice]`: runs the Stage 9 quality sampler and reports whether content came from AI or fallback generation.
- `clear-offline-questions`: deletes every archived offline question without touching learner progress, lesson history, or the wordbank.
- `seed-offline-questions [--topics ...] [--question-count N] [--goal lesson|review|practice]`: tops up the archived offline question bank. By default it targets the full A1-B2 roadmap and tries to reach at least 100 archived questions per topic.

Recommended usage:

- use `python main.py status` or `python main.py reset-progress` for ordinary local admin work
- use `.\run_server.bat status` or `.\run_server.bat seed-offline-questions` if the command should use the AI credentials configured in `run_server.bat`

Examples:

```powershell
python main.py status
python main.py reset-progress
python main.py set-progress --band B1
python main.py set-progress --level 9 --difficulty 10
python main.py sample-content --topics romanian_basics b2_core_structures
python main.py clear-offline-questions
python main.py seed-offline-questions
python main.py seed-offline-questions --topics romanian_basics b2_core_structures --question-count 100
```

If installed, the console script is also available:

```powershell
lumina-romana status
lumina-romana serve
```

`seed-offline-questions` does not guarantee that every topic will reach 100 stored questions. If AI is unavailable, or if only a smaller deterministic fallback pool exists for that topic, the command stores what it can and reports the shortfall. Running the command via `.\run_server.bat ...` is the supported way to ensure the batch-file AI config is applied.

## AI Configuration
The app reads AI settings from environment variables, including those set in `run_server.bat`.

Primary variables:

- `LUMINA_ROMANA_AI_ENABLED`
- `LUMINA_ROMANA_AI_PROVIDER`
- `LUMINA_ROMANA_AI_MODEL`
- `LUMINA_ROMANA_AI_API_KEY`
- `LUMINA_ROMANA_AI_BASE_URL`
- `LUMINA_ROMANA_AI_TIMEOUT_SECONDS`
- `LUMINA_ROMANA_AI_MAX_RETRIES`

Supported provider values:

- `gemini` or `google` for Gemini
- `copilot` for GitHub Copilot or another OpenAI-compatible endpoint
- `openai` for standard OpenAI-compatible chat completions

### Gemini example

```powershell
$env:LUMINA_ROMANA_AI_ENABLED = "true"
$env:LUMINA_ROMANA_AI_PROVIDER = "gemini"
$env:LUMINA_ROMANA_AI_MODEL = "gemini-2.5-flash"
$env:LUMINA_ROMANA_AI_API_KEY = "your-key"
```

### Copilot/OpenAI-compatible example

```powershell
$env:LUMINA_ROMANA_AI_ENABLED = "true"
$env:LUMINA_ROMANA_AI_PROVIDER = "copilot"
$env:LUMINA_ROMANA_AI_MODEL = "gpt-4.1"
$env:LUMINA_ROMANA_AI_API_KEY = "your-key"
$env:LUMINA_ROMANA_AI_BASE_URL = "https://your-openai-compatible-endpoint/v1"
```

Verification:

```powershell
python main.py status
```

Expected output includes:

```text
AI provider: gemini (..., configured=True)
```

or

```text
AI provider: copilot (..., configured=True)
```

## Persistence
Runtime data is stored in SQLite under the configured data directory.

The database currently stores:

- learner progress
- topic mastery
- skill scores
- lesson history
- quiz attempts
- pending incorrect-answer questions used by the Stage 11 mastery gate
- wordbank entries
- archived offline question bank entries

The `status` command reports the current offline question bank size, and the maintenance commands let you clear or repopulate that bank without touching learner progress.

Default database path:

```text
data/lumina_romana.db
```

## Testing
Run the full suite with:

```powershell
.\.venv\Scripts\python -m pytest -q
```

## Docker
An optional container runtime is included for the web app.

Build:

```powershell
docker build -t lumina-romana .
```

Run:

```powershell
docker run --rm -p 8000:8000 ^
  -e LUMINA_ROMANA_AI_ENABLED=true ^
  -e LUMINA_ROMANA_AI_PROVIDER=gemini ^
  -e LUMINA_ROMANA_AI_MODEL=gemini-2.5-flash ^
  -e LUMINA_ROMANA_AI_API_KEY=your-key ^
  -v ${PWD}\data:/app/data ^
  lumina-romana
```

See `docs/DEPLOYMENT.md` for the full local, wheel, and container deployment flows.

## Repository Layout
- `app/`: runtime package
- `tests/`: automated tests
- `docs/DEPLOYMENT.md`: deployment and update guide
- `plan.md`: staged delivery record
- `spec.md`: product and test specification
- `run_server.bat`: Windows startup script and AI config entrypoint

## Current Status
Implemented:

- Stage 0 foundation and packaging structure
- Stage 1 domain and SQLite persistence
- Stage 2 roadmap and prerequisite gating
- Stage 3 adaptive difficulty
- Stage 4 provider-backed AI generation
- Stage 5 validation and fallback content
- Stage 6 browser-based learner loop
- Stage 7 B1 integrated grammar tasks
- Stage 8 B2 reading and guided writing tasks
- Stage 9 metrics, sampling, and prompt-regression hardening
- Stage 10 packaging, deployment assets, and deployment documentation
- Stage 11 incorrect-answer persistence, remediation gating, and lesson-level question deduplication

Not implemented:

- authenticated multi-user accounts
- browser-based placement-test UI
- AI-assisted scoring of open writing responses
- production orchestration beyond local or container startup
