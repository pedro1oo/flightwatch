import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    # Google Flights API (SerpApi)
    SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "").strip()

    # SMTP Email
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str = os.getenv("SMTP_USER", "").strip()
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "").strip()
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "Passagens Baratas ✈️").strip()
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

    # App & Scheduler
    CHECK_INTERVAL_MINUTES: int = int(os.getenv("CHECK_INTERVAL_MINUTES", 60))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./flight_alerts.db")
    
    @property
    def is_flight_api_configured(self) -> bool:
        return bool(self.SERPAPI_KEY)

    @property
    def is_smtp_configured(self) -> bool:
        return bool(self.SMTP_USER and self.SMTP_PASSWORD)

settings = Settings()
