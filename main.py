"""Console entrypoint for Lumina Romana.

Provides the main CLI invocation used by the project executable. Keeps module very small
so the project can be executed as a script or installed as a console script.
"""
from app.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
