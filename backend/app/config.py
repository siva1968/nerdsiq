"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_env: str = "development"
    secret_key: str
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./nerdsiq.db"

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "nerdsiq_docs"

    # Google Drive
    google_service_account_file: str = "./credentials/google-service-account.json"
    google_drive_folder_id: str = ""
    
    # Google OAuth (alternative to service account for restricted orgs)
    google_oauth_client_file: str = "./credentials/oauth-client.json"
    google_oauth_token_file: str = "./credentials/oauth-token.json"
    google_auth_method: str = "auto"  # "service_account", "oauth", or "auto"

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # WordPress SSO
    wp_auth_secret: str = ""  # Shared secret for WordPress SSO
    
    # Email Configuration  
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    from_email: str = ""
    notification_emails: str = ""  # Comma-separated email addresses
    
    # Zepto Mail API Configuration (preferred over SMTP)
    zeptomail_api_key: str = ""  # Zoho API key
    zeptomail_region: str = "in"  # in, com, eu based on your region
    use_zeptomail_api: bool = True  # Use API instead of SMTP when available
    
    # Webhook Configuration
    webhook_callback_base_url: str = "https://your-domain.com"  # Base URL for webhook callbacks

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Rate Limiting
    rate_limit_per_minute: int = 30

    # Logging
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def notification_emails_list(self) -> list[str]:
        """Parse notification emails from comma-separated string."""
        if not self.notification_emails:
            return []
        return [email.strip() for email in self.notification_emails.split(",") if email.strip()]
    
    @property
    def zeptomail_api_url(self) -> str:
        """Get Zepto Mail API URL based on region."""
        region_map = {
            "in": "https://api.zeptomail.in/v1.1/email",
            "com": "https://api.zeptomail.com/v1.1/email", 
            "eu": "https://api.zeptomail.eu/v1.1/email"
        }
        return region_map.get(self.zeptomail_region, region_map["com"])

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
