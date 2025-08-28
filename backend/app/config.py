import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        self.app_name: str = os.getenv("APP_NAME", "CloudRTMP")
        self.secret_key: str = os.getenv("SECRET_KEY", "change-this-in-prod")
        self.algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes: int = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        )

        # Database
        self.database_url: str = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://postgres:postgres@db:5432/cloud_rtmp",
        )

        # File storage
        self.videos_dir: Path = Path(os.getenv("VIDEOS_DIR", "/videos"))

        # CORS
        self.cors_origins: str = os.getenv("CORS_ORIGINS", "*")

        # Streaming behavior
        self.auto_restart_streams: bool = os.getenv("AUTO_RESTART_STREAMS", "1") not in ("0", "false", "False")


settings = Settings()


