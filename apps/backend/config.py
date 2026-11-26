import os

from dotenv import load_dotenv

load_dotenv()

DSN = os.getenv("DATABASE_URL", "postgresql://bodesmart:bode2026@127.0.0.1:5432/bodesmart")
SECRET = os.getenv("BODESMART_SECRET", "bodesmart-dev-secret-change-me")
TOKEN_HOURS = 24
# operations-web (5173), customer-web (5174) and admin-web (5175), both
# hostnames for local dev. Production origins come from CORS_ORIGINS in .env.
CORS_ORIGINS = [origin.strip() for origin in os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:5174,http://127.0.0.1:5174,"
    "http://localhost:5175,http://127.0.0.1:5175",
).split(",") if origin.strip()]

# Demo-only checkout. Disable the local simulation and provide the test
# credentials before exposing this backend outside a local academic demo.
ALLOW_SIMULATED_PAYMENT = os.getenv("ALLOW_SIMULATED_PAYMENT", "true").lower() == "true"
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")
MERCADOPAGO_WEBHOOK_SECRET = os.getenv("MERCADOPAGO_WEBHOOK_SECRET", "")

# Gemini is decision support only. The key must stay in the backend.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# 3.5 flash-lite returned 503 service_unavailable under high demand during local testing.
# 3.1 flash-lite is available in v1/v1beta and aimed at high-volume, low-cost tasks.
# The UI may choose among these ids, but the backend is the only source of truth:
# a model sent by the browser is accepted only if it is in this allowlist.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
GEMINI_DEFAULT_MODELS = ("gemini-3.1-flash-lite", "gemini-3.5-flash-lite")


def _allowed_models(raw):
    items = [item.strip() for item in raw.split(",") if item.strip()]
    return tuple(dict.fromkeys(items or list(GEMINI_DEFAULT_MODELS)))


GEMINI_ALLOWED_MODELS = _allowed_models(os.getenv("GEMINI_ALLOWED_MODELS", ""))
if GEMINI_MODEL not in GEMINI_ALLOWED_MODELS:
    GEMINI_ALLOWED_MODELS = (GEMINI_MODEL,) + GEMINI_ALLOWED_MODELS
# v1 exposes the Interactions API for text, but inline image/audio blocks are
# only available in v1beta. One endpoint is shared by recommendations and REG-IA.
GEMINI_API_URL = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/interactions")

# Public barcode lookup for REG-IA. No key is required; the User-Agent lets the
# maintainers contact us if the prototype ever exceeds the published rate limit.
OPEN_FOOD_FACTS_API_URL = os.getenv(
    "OPEN_FOOD_FACTS_API_URL", "https://world.openfoodfacts.org/api/v2/product"
)
OPEN_FOOD_FACTS_USER_AGENT = os.getenv(
    "OPEN_FOOD_FACTS_USER_AGENT", "BodeSmart/0.1 (local-prototype)"
)
