from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = ""
    DATABASE_URL: str = ""
    FRONTEND_URL: str = ""
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env"}


settings = Settings()
