from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "api-main"
    debug: bool = False

    # OpenAI
    openai_api_key: SecretStr
    openai_model: str = "gpt-4o-mini"
    openai_max_output_tokens: int = Field(default=300, gt=0)

    # Chat safeguards
    chat_rate_limit_per_day: int = Field(default=10, gt=0)
    chat_max_message_characters: int = Field(default=1000, gt=0)
    chat_max_history_characters: int = Field(default=4000, gt=0)
    redis_url: str = "redis://localhost:6379/0"

    # Turnstile
    turnstile_secret_key: SecretStr
    turnstile_expected_hostname: str | None = "ivanpashkulev.com"
    turnstile_session_ttl_seconds: int = Field(default=86400, gt=0)
    turnstile_cookie_secure: bool = True

    # Assets
    assets_path: str = "assets"


settings = Settings()
