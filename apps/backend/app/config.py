from pathlib import Path
import os

BACKEND_DIR = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("BODEGA_DB_PATH", str(BACKEND_DIR / "bodega.db")))
CORS_ORIGINS = [origin.strip() for origin in os.getenv("BODEGA_CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
