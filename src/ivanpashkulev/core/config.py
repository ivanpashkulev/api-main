from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "api-main"
    debug: bool = False

    # Ollama
    ollama_base_url: str = "http://localhost:11434"

    # Assets
    assets_path: str = "assets"


settings = Settings()
