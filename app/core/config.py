import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Jeans Product API"
    
    # Database Settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/smgt"
    )
    
    # Google Gemini API
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    
    # CORS Settings
    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]
    
    POSTGRES_USER: str =os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: str|int = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB : str|int = os.getenv("POSTGRES_DB")


    MINIO_ROOT_USER: str = os.getenv("MINIO_ROOT_USER")
    MINIO_ROOT_PASSWORD: str = os.getenv("MINIO_ROOT_PASSWORD")
    MINIO_DOMAIN: str = os.getenv("MINIO_DOMAIN")
    MINIO_SERVER_URL: str = os.getenv("MINIO_SERVER_URL")
    MINIO_BUCKET_NAME: str = os.getenv("MINIO_BUCKET_NAME")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
