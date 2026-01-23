"""
Application configuration
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "Vaccination Locker API"
    API_VERSION: str = "v1"
    SECRET_KEY: str
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 3600
    
    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Google Cloud Platform
    GCP_PROJECT_ID: str
    GCP_REGION: str = "us-central1"
    GCS_BUCKET_NAME: str
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    
    # ABHA Integration
    ABHA_BASE_URL: Optional[str] = None  # Optional for development
    ABHA_CLIENT_ID: Optional[str] = None
    ABHA_CLIENT_SECRET: Optional[str] = None
    ABHA_ENABLED: bool = False  # Enable/disable ABHA features
    
    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    EMAIL_FROM: str
    
    # SMS/OTP Providers (msg91, gupshup, or console for dev)
    SMS_PROVIDER: str = "console"  # console, msg91, gupshup
    
    # MSG91 Configuration
    MSG91_AUTH_KEY: Optional[str] = None
    MSG91_TEMPLATE_ID: Optional[str] = None
    
    # Gupshup Configuration
    GUPSHUP_API_KEY: Optional[str] = None
    GUPSHUP_SOURCE: Optional[str] = None
    
    # Legacy Twilio (if needed)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    
    # WhatsApp
    WHATSAPP_PROVIDER: str = "twilio"
    WHATSAPP_ENABLED: bool = False
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # Security
    ALLOWED_HOSTS: List[str] = ["*"]
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # SUPER_ADMIN Bootstrap
    ALLOW_SUPER_ADMIN_SIGNUP: bool = False  # Set to true only during initial setup
    SUPER_ADMIN_BOOTSTRAP_TOKEN: Optional[str] = None  # Secure token for bootstrap
    
    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "jpg", "jpeg", "png"]
    
    # QR Code
    QR_CODE_EXPIRY_HOURS: int = 24
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env file


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()

