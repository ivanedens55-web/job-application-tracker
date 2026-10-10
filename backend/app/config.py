"""Settings read from environment variables (and a local .env file in development)."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # Does nothing if there is no .env file (e.g. on Render).


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    access_token_minutes: int
    cors_origins: list[str]
    environment: str

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


def load_settings() -> Settings:
    database_url = os.environ.get("DATABASE_URL", "")
    jwt_secret = os.environ.get("JWT_SECRET", "")
    origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]

    # Fail fast at startup with a clear message instead of failing on the first request.
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and fill it in.")
    if len(jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters long.")
    if "*" in origins:
        raise RuntimeError("CORS_ORIGINS must list exact URLs; '*' is not allowed.")

    return Settings(
        database_url=database_url,
        jwt_secret=jwt_secret,
        access_token_minutes=int(os.environ.get("ACCESS_TOKEN_MINUTES", "30")),
        cors_origins=origins,
        environment=os.environ.get("ENVIRONMENT", "development"),
    )
