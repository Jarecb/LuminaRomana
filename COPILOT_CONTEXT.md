# Copilot Context for LuminaRomana

## Purpose
A concise repository context file intended to give GitHub Copilot and contributors quick, focused information about this project so code suggestions and chat responses are accurate.

## Short description
LuminaRomana: a Python project with main.py, an app/ package, data/ and tests/. Primary goal: process and analyze Romanian text data (adjust as needed).

## Quick start
- Create a virtualenv: python -m venv .venv
- Activate: .\.venv\Scripts\activate
- Install: pip install -r requirements.txt (or use pyproject.toml / pip install -e .)
- Run: python main.py

## Key files & purpose
- main.py — entrypoint for commands and demo runs
- app/ — application code (modules and CLI/server)
- data/ — datasets and fixtures
- tests/ — unit and integration tests
- pyproject.toml — project metadata and deps

## Architecture overview
- Core modules live in app/; tests validate behavior in tests/.
- Data flows: data/ -> app.processing -> outputs/logs

## Common commands
- Run tests: pytest
- Lint/type-check: (project-specific tools)
- Start dev server: see run_server.bat or app/README

## Notes for Copilot
- Always code using TDD and Red/Green/Refactor techniques
- Always produce CLEAN and DRY code
- Focus on Pythonic idioms, small functions, and tests.
- When suggesting changes, prefer minimal, well-tested modifications.
- Highlight where sensitive data or large datasets are referenced.

## Known issues / TODOs
- Document high-priority TODOs here (e.g., missing CI, performance hotspots).

## Example prompts to include in PRs or issues
- "Add unit tests for app.module_x processing edge cases"
- "Refactor app.utils to reduce duplication"


---
Last updated: 2026-04-15
