from pydantic_settings import BaseSettings
from pydantic import PostgresDsn

class Settings(BaseSettings):
    PROJECT_NAME: str = "Clinic Booking API"
    API_V1_STR: str = "/api/v1"
    
#   DATABASE_URL: Postgres db  connectionstring  in the  .env  file
    DATABASE_URL: str 

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()