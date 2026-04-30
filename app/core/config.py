from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), env_file_encoding="utf-8")

    app_name: str = "ZenLife API"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./zenlife.db"

    # Auth
    secret_key: str = "zenlife-super-secret-key-change-in-production-2024"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # OTP (mock — in prod use Twilio/MSG91)
    otp_expire_minutes: int = 10
    mock_otp: str = "123456"

    # Anthropic (report extraction + health priorities)
    anthropic_api_key: str = ""

    # Google Gemini (Zeno AI chat)
    google_api_key: str = ""

    # CORS
    frontend_url: str = "http://localhost:3000"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
