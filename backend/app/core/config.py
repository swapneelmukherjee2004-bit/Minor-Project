"""Application settings, loaded from environment variables / .env."""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent


def _csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AccessAudit"
    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://auditor:auditor@localhost:5432/auditor"
    storage_dir: Path = BACKEND_DIR / "data" / "screenshots"
    dataset_dir: Path = REPO_DIR / "dataset"
    cors_origins: str = "http://localhost:5173"

    # AI provider: mock (demo mode, no credentials) | anthropic | openai_compatible
    ai_provider: Literal["mock", "anthropic", "openai_compatible"] = "mock"
    ai_model: str = "claude-sonnet-5-5"
    ai_api_key: SecretStr | None = None
    ai_base_url: str = ""
    ai_timeout_seconds: float = 90.0
    ai_max_retries: int = 3
    ai_max_output_tokens: int = 4096
    prompt_version: str = "audit-v1"

    # Browser / SSRF controls
    browser_executable_path: str = ""
    browser_no_sandbox: bool = False
    nav_timeout_ms: int = 30000
    max_requests_per_page: int = 400
    max_screenshot_height: int = 8000
    viewport_width: int = 1280
    viewport_height: int = 800
    max_concurrent_audits: int = 2
    max_pending_audits: int = 20
    # Comma separated origins (e.g. http://127.0.0.1:8000) allowed ONLY for paths under /fixtures/
    local_fixture_origins: str = ""

    rate_limit_audits: str = "10/minute"
    rate_limit_default: str = "120/minute"

    wcag_version: str = "2.2"
    wcag_levels: str = "A,AA"

    @property
    def cors_origin_list(self) -> list[str]:
        return _csv(self.cors_origins)

    @property
    def fixture_origin_set(self) -> set[str]:
        return {o.rstrip("/").lower() for o in _csv(self.local_fixture_origins)}

    @property
    def demo_mode(self) -> bool:
        return self.ai_provider == "mock"

    @property
    def ai_configured(self) -> bool:
        if self.ai_provider == "mock":
            return True
        if self.ai_provider == "openai_compatible" and not self.ai_base_url:
            return False
        return bool(self.ai_api_key and self.ai_api_key.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    return Settings()
