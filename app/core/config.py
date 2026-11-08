from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, gt=0)
    bcrypt_rounds: int = Field(default=12, ge=4, le=16)

    student_email_domain: str = "iiitdmj.ac.in"

    create_tables_on_startup: bool = True
    urgency_job_enabled: bool = True
    urgent_after_days: int = Field(default=7, gt=0)
    urgency_check_interval_minutes: int = Field(default=60, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
