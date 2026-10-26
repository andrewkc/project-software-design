from django.contrib import admin
from django.urls import path

from core import api


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health", api.health),
    path("api/v1/auth/csrf", api.csrf),
    path("api/v1/auth/login", api.login),
    path("api/v1/auth/logout", api.logout),
    path("api/v1/auth/me", api.me),
    path("api/v1/stores", api.stores),
]

