import os

DSN = os.getenv("DATABASE_URL", "postgresql://bodesmart:bode2026@127.0.0.1:5432/bodesmart")
SECRET = os.getenv("BODESMART_SECRET", "bodesmart-dev-secret-change-me")
TOKEN_HOURS = 24
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
