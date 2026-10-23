import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "debateIA Realtime Assist"
    DEBUG: bool = False

    # Database & pgvector
    DATABASE_URL: str = "postgresql+asyncpg://postgres:secret_password_change_me@localhost:5432/debateia"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "secret_password_change_me"
    POSTGRES_DB: str = "debateia"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432

    # LLM (DeepSeek V3)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Search APIs
    TAVILY_API_KEY: str = ""
    BRAVE_API_KEY: str = ""

    # Biometrics & Audio
    CANDIDATE_PROFILE_PATH: str = "/app/candidate_profile.npy"
    SPEAKER_SIMILARITY_THRESHOLD: float = 0.70
    WHISPER_MODEL_SIZE: str = "base"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"
    VAD_THRESHOLD: float = 0.5
    SILENCE_DURATION_MS: int = 400
    MAX_UTTERANCE_MS: int = 4500

    # Google Drive Sync
    GOOGLE_DRIVE_FOLDER_ID: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = "/app/service_account.json"
    GOOGLE_SERVICE_ACCOUNT_B64: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
