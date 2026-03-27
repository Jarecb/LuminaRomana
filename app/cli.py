from __future__ import annotations

from collections.abc import Sequence
import argparse
import shutil
import sys

from app.bootstrap import create_application
from app.ui import run_dev_server


CEFR_TO_LEVEL = {
    "A1": 1,
    "A2": 5,
    "B1": 7,
    "B2": 9,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lumina-romana")
    subcommands = parser.add_subparsers(dest="command")
    subcommands.add_parser("serve", help="Run the browser-based learner interface.")
    subcommands.add_parser("status", help="Print configuration and runtime status.")
    subcommands.add_parser("reset-progress", help="Reset the default learner's local progress for testing.")
    set_progress_parser = subcommands.add_parser(
        "set-progress",
        help="Jump the default learner to a testing level or CEFR band.",
    )
    target_group = set_progress_parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--band", choices=tuple(CEFR_TO_LEVEL), help="Jump to the first level of a CEFR band.")
    target_group.add_argument("--level", type=int, help="Jump to an exact roadmap level.")
    set_progress_parser.add_argument(
        "--difficulty",
        type=int,
        help="Override the default testing difficulty for the target position.",
    )
    args = parser.parse_args(list(argv) if argv is not None else sys.argv[1:])

    app = create_application()
    command = args.command or "status"
    if command == "serve":
        run_dev_server(app)
        return 0
    if command == "reset-progress":
        progress = app.learning_service.reset_progress()
        print(f"Reset learner progress for {progress.user_id}.")
        print("Current level: 1")
        print("Current CEFR band: A1")
        print("Current difficulty: 1")
        return 0
    if command == "set-progress":
        target_level = args.level if args.level is not None else CEFR_TO_LEVEL[args.band]
        progress = app.learning_service.set_testing_position(
            level=target_level,
            difficulty=args.difficulty,
        )
        next_topic = app.content_library.next_topic_for_user(progress)
        next_topic_label = next_topic.title if next_topic is not None else "Roadmap complete"
        print(f"Set learner progress for {progress.user_id}.")
        print(f"Current level: {progress.current_level}")
        print(f"Current CEFR band: {progress.current_cefr_band.value}")
        print(f"Current difficulty: {progress.current_difficulty}")
        print(f"Next topic: {next_topic_label}")
        return 0

    app.logger.info("Loading %s diagnostics in %s mode", app.settings.app_name, app.settings.environment)
    print(f"{app.settings.app_name} developer status")
    print(f"Environment: {app.settings.environment}")
    print(f"Data directory: {app.settings.data_dir}")
    print(f"Database path: {app.settings.database_path}")
    print(f"Seed topics loaded: {len(app.content_library.all_topics())}")
    print(
        "AI provider: "
        f"{app.ai_service.provider.provider_name} "
        f"({app.ai_service.provider.model}, configured={app.ai_service.is_configured})"
    )
    print(f"Web UI: http://{app.settings.web.host}:{app.settings.web.port}")
    print("Run `python main.py serve` to start the browser-based learner interface from this checkout.")
    if shutil.which("lumina-romana"):
        print("Installed console script available: `lumina-romana serve`.")
    else:
        print("Install with `pip install -e .` if you want the `lumina-romana` command in your environment.")
    return 0
