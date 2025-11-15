"""
Configuration settings for EchoGuard
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://echoguard:echoguard@localhost:5432/echoguard"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    
    # ML Model
    MODEL_PATH: str = "./models/echoguard_model.h5"
    AUDIO_CHUNK_DURATION: float = 5.0
    SAMPLE_RATE: int = 22050
    
    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Alerts
    ALERT_WEBHOOK_URL: str = ""
    ENABLE_ALERTS: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

