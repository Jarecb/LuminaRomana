from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(slots=True)
class Settings:
    app_name: str = "Lumina Romana"
    environment: str = "development"
    log_level: str = "INFO"
    data_dir: Path = Path("data")
    database_path: Path = Path("data/lumina_romana.db")

    @classmethod
    def load(cls) -> "Settings":
        data_dir = Path(os.getenv("LUMINA_ROMANA_DATA_DIR", "data")).expanduser()
        database_path = Path(
            os.getenv("LUMINA_ROMANA_DB_PATH", str(data_dir / "lumina_romana.db"))
        ).expanduser()
        return cls(
            environment=os.getenv("LUMINA_ROMANA_ENV", "development"),
            log_level=os.getenv("LUMINA_ROMANA_LOG_LEVEL", "INFO").upper(),
            data_dir=data_dir,
            database_path=database_path,
        )
