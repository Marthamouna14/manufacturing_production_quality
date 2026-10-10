from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    app_name: str = "Manufacturing Production & Quality Control API"
    secret_key: str = "CHANGE_ME_IN_ENV"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    database_url: str = "sqlite:///./manufacturing.db"
    cors_origins: str = "*"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings = Settings()
