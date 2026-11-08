from django.contrib import admin
from django.urls import path

from core import api


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health", api.health),
    path("api/v1/auth/csrf", api.csrf),
    path("api/v1/auth/login", api.login),
    path("api/v1/auth/register", api.register_customer),
    path("api/v1/auth/logout", api.logout),
    path("api/v1/auth/me", api.me),
    path("api/v1/stores", api.stores),
    path("api/v1/offers", api.public_offers),
    path("api/v1/offers/<uuid:offer_id>", api.public_offer),
    path("api/v1/orders", api.orders),
    path("api/v1/orders/<uuid:order_id>", api.order_detail),
    path("api/v1/orders/<uuid:order_id>/simulate-payment", api.simulated_payment),
    path("api/v1/chat", api.local_chat),
    path("api/v1/store/products", api.store_products),
    path("api/v1/store/lots", api.store_lots),
    path("api/v1/store/inbounds", api.store_inbounds),
    path("api/v1/store/local-sales", api.store_sales),
    path("api/v1/store/waste", api.store_waste),
    path("api/v1/store/adjustments", api.store_adjustments),
    path("api/v1/store/movements", api.store_movements),
    path("api/v1/store/offers", api.store_offers),
    path("api/v1/store/offers/<uuid:offer_id>/publish", api.offer_publish),
    path("api/v1/store/offers/<uuid:offer_id>/pause", api.offer_pause),
    path("api/v1/store/offers/<uuid:offer_id>/limits", api.offer_limits),
    path("api/v1/store/offers/<uuid:offer_id>/price", api.offer_price),
    path("api/v1/store/analysis", api.store_analysis),
    path("api/v1/store/recommendations", api.store_recommendations),
    path("api/v1/store/recommendations/<uuid:recommendation_id>/decision", api.recommendation_decision),
]

