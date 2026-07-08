import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Slip Verification Service"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "slip_db")
    DATABASE_URL: str = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}/{POSTGRES_DB}"

    # Storage
    STORAGE_TYPE: str = "local" # local, s3, etc.
    UPLOAD_DIR: str = "storage/uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024 # 10MB
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png"]

    # OCR
    OCR_LANGUAGES: List[str] = ["th", "en"]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
