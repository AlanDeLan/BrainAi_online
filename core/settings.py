"""
Production-ready configuration management using Pydantic Settings.
Environment variables override defaults.
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # === Application Settings ===
    app_name: str = "BrainAi"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    secret_key: str = Field(default="dev-secret-key-change-in-production", alias="SECRET_KEY")
    
    # === Server Settings ===
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    
    # === Database Settings ===
    database_url: str = Field(default="sqlite:///./brainai.db", alias="DATABASE_URL")  # SQLite fallback
    
    @field_validator("database_url")
    @classmethod
    def clean_database_url(cls, v):
        """Remove Railway template syntax from DATABASE_URL."""
        import os
        # Debug logging
        raw_url = os.environ.get('DATABASE_URL', 'NOT_SET')
        print(f"DEBUG: Raw DATABASE_URL from env: {raw_url[:50]}...")
        print(f"DEBUG: Received in validator: {v[:50] if v else 'None'}...")
        
        if v and v.startswith("${{") and v.endswith("}}"):
            # Extract actual URL from ${{...}}
            v = v[3:-2].strip()
            print(f"DEBUG: Cleaned to: {v[:50]}...")
        return v
    
    # === AI Provider Settings ===
    ai_provider: str = Field(default="google_ai", alias="AI_PROVIDER")
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        alias="OPENAI_BASE_URL"
    )
    
    # === Security Settings ===
    session_secret: str = Field(default="dev-session-secret-change-in-production", alias="SESSION_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, alias="JWT_EXPIRATION_HOURS")
    
    # === CORS Settings ===
    cors_origins: List[str] = Field(
        default=["http://localhost:8000"],
        alias="CORS_ORIGINS"
    )
    allow_credentials: bool = Field(default=True, alias="ALLOW_CREDENTIALS")
    
    # === Rate Limiting ===
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=1000, alias="RATE_LIMIT_PER_HOUR")
    
    # === Logging Settings ===
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # === Admin Settings ===
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="admin123", alias="ADMIN_PASSWORD")  # Default for development
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra env vars
    )
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment value."""
        allowed = ["development", "staging", "production"]
        if v.lower() not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v.lower()
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of: {allowed}")
        return v.upper()
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"


# Global settings instance
try:
    settings = Settings()
except Exception as e:
    print(f"⚠️  Error loading settings: {e}")
    print("Please ensure all required environment variables are set in .env file")
    raise
