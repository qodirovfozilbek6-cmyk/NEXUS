
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
    WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip().rstrip("/")
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    DATABASE_PATH = os.getenv(
        "DATABASE_PATH", "data/nexus.sqlite3"
    )
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    @classmethod
    def validate_bot(cls):
        if not cls.BOT_TOKEN:
            raise RuntimeError(
                "BOT_TOKEN topilmadi. .env faylini tekshir."
            )

    @classmethod
    def database_file(cls):
        path = Path(cls.DATABASE_PATH)
        if not path.is_absolute():
            path = BASE_DIR / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)


settings = Settings()