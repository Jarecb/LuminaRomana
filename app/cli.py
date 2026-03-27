from __future__ import annotations

from collections.abc import Sequence
import argparse
import shutil
import sys

from app.bootstrap import create_application
from app.ui import run_dev_server


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lumina-romana")
    subcommands = parser.add_subparsers(dest="command")
    subcommands.add_parser("serve", help="Run the browser-based learner interface.")
    subcommands.add_parser("status", help="Print configuration and runtime status.")
    args = parser.parse_args(list(argv) if argv is not None else sys.argv[1:])

    app = create_application()
    command = args.command or "status"
    if command == "serve":
        run_dev_server(app)
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
