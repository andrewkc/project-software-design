import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DSN = os.getenv("DATABASE_URL", "postgresql://bodesmart:bode2026@127.0.0.1:5432/bodesmart")
SECRET = os.getenv("BODESMART_SECRET", "bodesmart-dev-secret-change-me")
TOKEN_HOURS = 24
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174").split(",") if origin.strip()]
