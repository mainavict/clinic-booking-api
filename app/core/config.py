from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Clinic Booking API"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str
    SENTRY_DSN: Optional[str] = None #local dev doesn't crash if missing

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()