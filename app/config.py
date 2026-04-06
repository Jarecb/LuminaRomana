from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class AISettings:
    enabled: bool = False
    offline_only: bool = False
    provider: str = "openai"
    model: str = "gpt-4.1-mini"
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: float = 30.0
    max_retries: int = 2

    @property
    def is_configured(self) -> bool:
        return not self.offline_only and self.enabled and bool(self.api_key)

    @property
    def configured(self) -> bool:
        return self.is_configured


@dataclass(slots=True)
class WebSettings:
    host: str = "127.0.0.1"
    port: int = 8000


@dataclass(slots=True)
class Settings:
    app_name: str = "Lumina Romana"
    environment: str = "development"
    log_level: str = "INFO"
    data_dir: Path = Path("data")
    database_path: Path = Path("data/lumina_romana.db")
    ai: AISettings = field(default_factory=AISettings)
    web: WebSettings = field(default_factory=WebSettings)

    @classmethod
    def load(cls, *, offline_only: bool = False) -> "Settings":
        data_dir = Path(os.getenv("LUMINA_ROMANA_DATA_DIR", "data")).expanduser()
        database_path = Path(
            os.getenv("LUMINA_ROMANA_DB_PATH", str(data_dir / "lumina_romana.db"))
        ).expanduser()
        api_key = os.getenv("LUMINA_ROMANA_AI_API_KEY")
        return cls(
            environment=os.getenv("LUMINA_ROMANA_ENV", "development"),
            log_level=os.getenv("LUMINA_ROMANA_LOG_LEVEL", "INFO").upper(),
            data_dir=data_dir,
            database_path=database_path,
            ai=AISettings(
                enabled=_env_flag("LUMINA_ROMANA_AI_ENABLED", default=bool(api_key)),
                offline_only=offline_only or _env_flag("LUMINA_ROMANA_AI_OFFLINE_ONLY", default=False),
                provider=os.getenv("LUMINA_ROMANA_AI_PROVIDER", "openai").lower(),
                model=os.getenv("LUMINA_ROMANA_AI_MODEL", "gpt-4.1-mini"),
                api_key=api_key,
                base_url=os.getenv("LUMINA_ROMANA_AI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
                timeout_seconds=float(os.getenv("LUMINA_ROMANA_AI_TIMEOUT_SECONDS", "30")),
                max_retries=max(0, int(os.getenv("LUMINA_ROMANA_AI_MAX_RETRIES", "2"))),
            ),
            web=WebSettings(
                host=os.getenv("LUMINA_ROMANA_WEB_HOST", "127.0.0.1"),
                port=int(os.getenv("LUMINA_ROMANA_WEB_PORT", "8000")),
            ),
        )
