"""Read-only chat boundary. Phase 4 may replace the local responder with Gemini."""

from . import commerce, services
from .models import Lot, User


def facts_for(actor, question):
    """Return only permitted, bounded facts; never accept arbitrary SQL or store IDs."""
    text = question.lower()
    if actor.is_authenticated and actor.is_active and actor.role in (User.Role.OWNER, User.Role.EMPLOYEE):
        services.require_staff(actor)
        if any(word in text for word in ("stock", "inventario", "venc", "lote")):
            lots = Lot.objects.select_related("product").filter(
                product__store_id=actor.store_id, active=True).order_by("expiry_date")[:10]
            return {"kind": "inventory", "store": actor.store.name,
                    "lots": [{"product": lot.product.name, "code": lot.code,
                              "available": lot.available_qty, "expiry": lot.expiry_date.isoformat()}
                             for lot in lots]}
    offers = commerce.public_offers()
    if actor.is_authenticated and actor.is_active and actor.role in (User.Role.OWNER, User.Role.EMPLOYEE):
        offers = [offer for offer in offers if offer.lot.product.store_id == actor.store_id]
    return {"kind": "offers", "offers": [commerce.offer_payload(offer) for offer in offers[:10]]}


class LocalChatProvider:
    """Deterministic demo responder with the same facts interface as a future provider."""

    def respond(self, question, facts):
        if facts["kind"] == "inventory":
            if not facts["lots"]:
                return "No hay lotes activos en tu bodega."
            return "Lotes de tu bodega: " + "; ".join(
                f"{item['product']} ({item['code']}): {item['available']} disponibles, vence {item['expiry']}"
                for item in facts["lots"])
        if not facts["offers"]:
            return "No hay ofertas publicadas y disponibles ahora."
        return "Ofertas disponibles: " + "; ".join(
            f"{item['product_name']} en {item['store_name']}: S/ {item['current_price']} por "
            f"{item['sale_step']} {item['unit']}" for item in facts["offers"])


def answer(actor, question, provider=None):
    if not isinstance(question, str) or not 1 <= len(question.strip()) <= 1000:
        raise services.DomainError("INVALID_QUESTION", "La pregunta debe tener entre 1 y 1000 caracteres")
    facts = facts_for(actor, question.strip())
    responder = provider or LocalChatProvider()
    return {"answer": responder.respond(question.strip(), facts), "mode": "LOCAL_DEMO"}
