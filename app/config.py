import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    database_url: str = ""
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    def get_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        env_url = os.environ.get("DATABASE_URL")
        if env_url:
            return env_url.replace("postgres://", "postgresql://", 1)
        return f"sqlite:///{DATA_DIR / 'portfolio.db'}"

settings = Settings()
