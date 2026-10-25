from pydantic_settings import BaseSettings
from typing import Optional
from datetime import time

class Settings(BaseSettings):
    PROJECT_NAME: str = "Clinic Booking API"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str
    SENTRY_DSN: Optional[str] = None
    MAX_DAYS_IN_ADVANCE: int = 14
    
    # Default working hours for new doctors
    DEFAULT_WORK_HOURS_START: time = time(9, 0)
    DEFAULT_WORK_HOURS_END: time = time(17, 0)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()