from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FastAPI Multi-Gateway Payment Platform"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./payment.db"
    stripe_webhook_secret: str = ""
    paypal_webhook_secret: str = ""
    plaid_webhook_secret: str = ""
    audit_queue_size: int = 1000

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
