"""Phase 1 API: identity and public store discovery."""

from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Store


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

