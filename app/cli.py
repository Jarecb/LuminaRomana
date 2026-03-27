from __future__ import annotations

from app.bootstrap import create_application


def main() -> int:
    app = create_application()
    app.logger.info(
        "Starting %s in %s mode",
        app.settings.app_name,
        app.settings.environment,
    )
    print(f"{app.settings.app_name} is ready.")
    print(f"Environment: {app.settings.environment}")
    print(f"Data directory: {app.settings.data_dir}")
    print(f"Database path: {app.settings.database_path}")
    print(f"Seed topics loaded: {len(app.content_library.all_topics())}")
    return 0
