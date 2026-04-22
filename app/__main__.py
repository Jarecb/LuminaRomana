"""Console script entrypoint for Lumina Romana's installed command.

Delegates to the CLI implementation in app.cli so the package can be executed
as a module or installed as a console script.
"""
from app.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
