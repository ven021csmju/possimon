from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "PoSimon Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Security
    SECRET_KEY: str = "dev_secret_key_change_me_in_prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: str = "sqlite:///./possimon.db"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "https://front-posimon.vercel.app",
        "https://front-posimon-a68ohduyv-ven-307s-projects.vercel.app",
        "https://the-bottle-club-ai.vercel.app",
        "https://the-bottle-club-qm0jkf1vb-knathip-sasibut-310s-projects.vercel.app",
        "https://pos-frontend.vercel.app",
        "https://web-frontend.vercel.app",
        "https://administratunegocio.club",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
    ]
    
    # External APIs
    API_KEY: str = "" # Map directly to API_KEY in .env
    FRONTEND_URL: str = "https://front-posimon.vercel.app/auth/success"
    WEB_FRONTEND_URL: Optional[str] = None
    POS_FRONTEND_URL: Optional[str] = None
    
    # Auth Roles
    POS_ALLOWED_ROLES: List[str] = ["admin", "manager", "cashier", "customer"]
    
    # Social Login
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    LINE_CHANNEL_ID: Optional[str] = None
    LINE_CHANNEL_SECRET: Optional[str] = None
    FACEBOOK_APP_ID: Optional[str] = None
    FACEBOOK_APP_SECRET: Optional[str] = None
    
    # Cookie Settings
    COOKIE_NAME: str = "access_token"
    REFRESH_COOKIE_NAME: str = "refresh_token"
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "none" # "lax", "strict", or "none"
    COOKIE_DOMAIN: Optional[str] = None # Set to your domain in production

    # Environment
    ENV: str = "dev" # dev, production

    # File Storage
    UPLOAD_DIR: str = "uploads"
    PRODUCTS_IMAGE_DIR: str = "products"
    STATIC_URL_PREFIX: str = "/static"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore" # Allow extra env variables without crashing
    )

    @model_validator(mode="after")
    def set_frontend_url_defaults(self):
        if not self.WEB_FRONTEND_URL:
            self.WEB_FRONTEND_URL = self.FRONTEND_URL
        if not self.POS_FRONTEND_URL:
            self.POS_FRONTEND_URL = self.FRONTEND_URL
        return self

settings = Settings()
