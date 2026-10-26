"""Small JSON API. Business rules live in services, not in HTTP handlers."""

from django.db import IntegrityError
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import InventoryMovement, Lot, Offer, OfferLimit, Order, Product, Store, User
from . import chat, commerce, services


def user_payload(user):
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "store_id": str(user.store_id) if user.store_id else None,
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok", "phase": 1})


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf(request):
    return Response({"csrf_token": get_token(request)})


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
def login(request):
    email = str(request.data.get("email", "")).strip().lower()
    password = str(request.data.get("password", ""))
    user = authenticate(request, email=email, password=password)
    if user is None or not user.is_active:
        return Response({"error": {"code": "INVALID_CREDENTIALS", "message": "Credenciales inválidas"}}, status=status.HTTP_401_UNAUTHORIZED)
    django_login(request, user)
    return Response(user_payload(user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    django_logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    if not request.user.is_active:
        return Response({"error": {"code": "INACTIVE", "message": "Cuenta desactivada"}}, status=status.HTTP_403_FORBIDDEN)
    return Response(user_payload(request.user))


@api_view(["GET"])
@permission_classes([AllowAny])
def stores(request):
    data = [{"id": str(store.id), "name": store.name, "address": store.address, "opening_hours": store.opening_hours}
            for store in Store.objects.filter(active=True).order_by("name")]
    return Response(data)


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
def register_customer(request):
    def create():
        email = str(request.data.get("email", "")).strip().lower()
        name = services.required_text(request.data.get("name"), "Nombre", 120)
        password = request.data.get("password")
        if not isinstance(password, str):
            raise services.DomainError("INVALID_PASSWORD", "Contraseña inválida")
        user = User(email=email, name=name, role=User.Role.CUSTOMER)
        try:
            validate_password(password, user)
        except ValidationError as error:
            raise services.DomainError("INVALID_PASSWORD", "; ".join(error.messages)) from error
        try:
            return User.objects.create_user(email=email, password=password, name=name, role=User.Role.CUSTOMER)
        except ValidationError as error:
            raise services.DomainError("INVALID_DATA", "; ".join(error.messages)) from error
    return _execute(create, user_payload, 201)


@api_view(["GET"])
@permission_classes([AllowAny])
def public_offers(request):
    def read():
        commerce.expire_due_orders()
        return [commerce.offer_payload(offer) for offer in commerce.public_offers(request.query_params.get("store_id"))]
    return _execute(read)


@api_view(["GET"])
@permission_classes([AllowAny])
def public_offer(request, offer_id):
    def read():
        commerce.expire_due_orders()
        offer = next((item for item in commerce.public_offers() if item.id == offer_id), None)
        if not offer:
            raise services.DomainError("NOT_FOUND", "Oferta no encontrada", 404)
        return commerce.offer_payload(offer)
    return _execute(read)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def orders(request):
    if request.method == "POST":
        def create():
            commerce.expire_due_orders()
            return commerce.create_order(request.user, request.data)
        return _execute(create, commerce.order_payload, 201)

    def read():
        commerce.require_customer(request.user)
        commerce.expire_due_orders()
        return [commerce.order_payload(order) for order in Order.objects.select_related("store").filter(
            customer=request.user).order_by("-created_at")[:50]]
    return _execute(read)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def order_detail(request, order_id):
    def read():
        order = commerce.get_order(request.user, order_id)
        commerce.expire_order(order.id)
        order.refresh_from_db()
        return commerce.order_payload(order)
    return _execute(read)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def simulated_payment(request, order_id):
    return _execute(lambda: commerce.simulate_payment(request.user, order_id,
                     request.data.get("decision")), commerce.order_payload)


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
def local_chat(request):
    return _execute(lambda: chat.answer(request.user, request.data.get("question")))


def _execute(action, serialize=lambda result: result, success=200):
    try:
        result = action()
        return Response(serialize(result), status=success)
    except services.DomainError as error:
        return Response({"error": {"code": error.code, "message": error.message}}, status=error.status)
    except IntegrityError:
        return Response({"error": {"code": "CONFLICT", "message": "El registro ya existe o contradice una restricción"}}, status=409)


def _product_payload(product):
    return {"id": str(product.id), "code": product.code, "name": product.name,
            "category": product.category, "unit": product.unit, "sale_step": product.sale_step,
            "reference_price": str(product.reference_price), "active": product.active}


def _lot_payload(lot, owner=False):
    data = {"id": str(lot.id), "product_id": str(lot.product_id), "product_name": lot.product.name,
            "code": lot.code, "received_date": lot.received_date.isoformat(),
            "expiry_date": lot.expiry_date.isoformat(), "sales_close_at": lot.sales_close_at.isoformat(),
            "received_qty": lot.received_qty, "physical_qty": lot.physical_qty,
            "reserved_qty": lot.reserved_qty, "available_qty": lot.available_qty, "active": lot.active}
    if owner:
        data["total_cost"] = str(lot.total_cost)
    return data


def _offer_payload(offer, owner=False):
    data = {"id": str(offer.id), "lot_id": str(offer.lot_id), "product_id": str(offer.lot.product_id),
            "product_name": offer.lot.product.name, "lot_code": offer.lot.code,
            "expiry_date": offer.lot.expiry_date.isoformat(), "available_qty": offer.lot.available_qty,
            "sale_step": offer.lot.product.sale_step, "unit": offer.lot.product.unit,
            "state": offer.state, "original_price": str(offer.original_price),
            "current_price": str(offer.current_price), "version": offer.version,
            "automation_paused": offer.automation_paused}
    if owner:
        limit = OfferLimit.objects.filter(offer=offer, ends_at__isnull=True).first()
        data["limit"] = {"version": limit.version, "max_discount_pct": str(limit.max_discount_pct),
                         "minimum_price": str(limit.minimum_price),
                         "below_cost_authorized": limit.below_cost_authorized,
                         "effective_floor": str(services.price_floor(offer, limit))} if limit else None
    return data


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def store_products(request):
    if request.method == "POST":
        return _execute(lambda: services.create_product(request.user, request.data), _product_payload, 201)

    def get_data():
        services.require_staff(request.user)
        return [_product_payload(p) for p in Product.objects.filter(store_id=request.user.store_id).order_by("name", "code")]
    return _execute(get_data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def store_lots(request):
    def get_data():
        services.require_staff(request.user)
        owner = request.user.role == User.Role.OWNER
        lots = Lot.objects.select_related("product").filter(product__store_id=request.user.store_id).order_by("sales_close_at", "code")
        return [_lot_payload(lot, owner) for lot in lots]
    return _execute(get_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def store_inbounds(request):
    return _execute(lambda: services.create_inbound(request.user, request.data),
                    lambda pair: {"lot": _lot_payload(pair[0], True), "movement": services.movement_result(pair[1])}, 201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def store_sales(request):
    return _execute(lambda: services.sell_local(request.user, request.data), services.movement_result, 201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def store_waste(request):
    return _execute(lambda: services.waste(request.user, request.data), services.movement_result, 201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def store_adjustments(request):
    return _execute(lambda: services.adjust(request.user, request.data), services.movement_result, 201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def store_movements(request):
    def get_data():
        services.require_staff(request.user)
        movements = InventoryMovement.objects.filter(store_id=request.user.store_id).order_by("-confirmed_at", "-created_at")[:100]
        return [services.movement_result(m) for m in movements]
    return _execute(get_data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def store_offers(request):
    def get_data():
        services.require_staff(request.user)
        owner = request.user.role == User.Role.OWNER
        offers = Offer.objects.select_related("lot__product").filter(lot__product__store_id=request.user.store_id).order_by("lot__sales_close_at", "lot__code")
        return [_offer_payload(offer, owner) for offer in offers]
    return _execute(get_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def offer_publish(request, offer_id):
    return _execute(lambda: services.publish_offer(request.user, offer_id), lambda offer: _offer_payload(offer, True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def offer_pause(request, offer_id):
    return _execute(lambda: services.pause_offer(request.user, offer_id), lambda offer: _offer_payload(offer, True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def offer_limits(request, offer_id):
    return _execute(lambda: services.set_offer_limit(request.user, offer_id, request.data),
                    lambda limit: _offer_payload(limit.offer, True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def offer_price(request, offer_id):
    return _execute(lambda: services.change_price(request.user, offer_id, request.data),
                    lambda change: {"id": str(change.id), "old_price": str(change.old_price),
                                    "new_price": str(change.new_price), "offer_id": str(change.offer_id)})

