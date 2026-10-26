"""Idempotent fictional fixture. Use only in an empty demo database."""

import os
import uuid
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import (
    InventoryMovement, Lot, MovementLine, Offer, OfferLimit, Product,
    Store, StorePricingPolicy, User,
)


PRODUCTS = [
    ("Mercado Verde", "ALM", "Almendras", "Frutos secos", "G", 250, 5000, 30, 20, "10.00"),
    ("Mercado Verde", "PAS", "Pasas", "Frutos secos", "G", 250, 3000, 20, 12, "6.00"),
    ("Mercado Verde", "FRE", "Fresas", "Frutas", "G", 250, 2000, 7, 2, "5.00"),
    ("Mercado Verde", "MAN", "Manzanas", "Frutas", "G", 500, 6000, 10, 5, "5.00"),
    ("Dulce y Fresco", "PAT", "Pastel entero", "Repostería", "UNIT", 1, 6, 7, 2, "20.00"),
    ("Dulce y Fresco", "NUE", "Nueces", "Frutos secos", "G", 250, 4000, 30, 15, "12.00"),
    ("Dulce y Fresco", "ARA", "Arándanos", "Frutas", "G", 125, 1000, 7, 3, "6.00"),
    ("Dulce y Fresco", "UVA", "Uvas", "Frutas", "G", 500, 4000, 7, 4, "7.00"),
    ("Despensa Cercana", "PLA", "Plátanos", "Frutas", "G", 500, 5000, 7, 3, "4.00"),
    ("Despensa Cercana", "MNG", "Mangos", "Frutas", "UNIT", 1, 12, 7, 4, "4.00"),
    ("Despensa Cercana", "DAT", "Dátiles", "Frutos secos", "G", 250, 2000, 30, 18, "9.00"),
    ("Despensa Cercana", "QUE", "Queque entero", "Repostería", "UNIT", 1, 8, 7, 2, "14.00"),
]


class Command(BaseCommand):
    help = "Carga tres bodegas y datos ficticios una sola vez, en una base vacía"

    def handle(self, *args, **options):
        password = os.getenv("DESSOF_DEMO_PASSWORD")
        if not password or len(password) < 12:
            raise CommandError("Configura DESSOF_DEMO_PASSWORD con al menos 12 caracteres")
        if Store.objects.exists():
            raise CommandError("La carga demo solo se permite en una base sin tiendas")
        today = timezone.localdate()
        with transaction.atomic():
            stores = {}
            owners = {}
            for index, name in enumerate(["Mercado Verde", "Dulce y Fresco", "Despensa Cercana"], 1):
                store = Store.objects.create(name=name, address=f"Dirección ficticia {index}, Lima")
                stores[name] = store
                owner = User.objects.create_user(email=f"dueno.{index}@demo.example", password=password,
                                                 name=f"Dueño demo {index}", role=User.Role.OWNER, store=store)
                User.objects.create_user(email=f"empleado.{index}@demo.example", password=password,
                                         name=f"Empleado demo {index}", role=User.Role.EMPLOYEE, store=store)
                owners[name] = owner
                StorePricingPolicy.objects.create(store=store, version=1, mode=StorePricingPolicy.Mode.REVIEW,
                                                  starts_at=timezone.now(), created_by=owner)
            User.objects.create_user(email="admin@demo.example", password=password, name="Admin demo", role=User.Role.ADMIN,
                                     is_staff=True, is_superuser=True)
            for index in (1, 2):
                User.objects.create_user(email=f"cliente.{index}@demo.example", password=password,
                                         name=f"Cliente demo {index}", role=User.Role.CUSTOMER)

            for store_name, code, name, category, unit, step, qty, duration, remaining, price_text in PRODUCTS:
                store = stores[store_name]
                price = Decimal(price_text)
                product = Product.objects.create(store=store, code=code, name=name, category=category,
                                                 unit=unit, sale_step=step, reference_price=price,
                                                 storage_conditions="Condiciones ficticias; validar antes de uso real")
                expiry = today + timedelta(days=remaining)
                received = expiry - timedelta(days=duration)
                close = datetime.combine(expiry - timedelta(days=1), time(23, 59, 59), ZoneInfo("America/Lima"))
                cost = (price * Decimal("0.5") * Decimal(qty) / Decimal(step)).quantize(Decimal("0.01"))
                lot = Lot.objects.create(product=product, code=f"{code}-01", received_date=received,
                                         expiry_date=expiry, sales_close_at=close, total_cost=cost,
                                         received_qty=qty)
                self._receive(lot, qty, owners[store_name], f"fixture-{store_name}-{code}-01")
                offer = Offer.objects.create(lot=lot, state=Offer.State.PUBLISHED,
                                             original_price=price, current_price=price)
                OfferLimit.objects.create(offer=offer, version=1, max_discount_pct=Decimal("30.00"),
                                          minimum_price=(price * Decimal("0.7")).quantize(Decimal("0.01")),
                                          below_cost_authorized=False, authorized_by=owners[store_name],
                                          starts_at=timezone.now())
                # A second, smaller lot in each store proves that lot size and dates are independent.
                if code in ("ALM", "NUE", "DAT"):
                    second_qty = step * 3
                    second_expiry = today + timedelta(days=remaining + 4)
                    second_cost = (price * Decimal("0.5") * Decimal(3)).quantize(Decimal("0.01"))
                    second = Lot.objects.create(product=product, code=f"{code}-02",
                                                received_date=second_expiry - timedelta(days=duration),
                                                expiry_date=second_expiry,
                                                sales_close_at=datetime.combine(second_expiry - timedelta(days=1), time(23, 59, 59), ZoneInfo("America/Lima")),
                                                total_cost=second_cost, received_qty=second_qty)
                    self._receive(second, second_qty, owners[store_name], f"fixture-{store_name}-{code}-02")
                    second_offer = Offer.objects.create(lot=second, state=Offer.State.PUBLISHED,
                                                        original_price=price, current_price=price)
                    OfferLimit.objects.create(offer=second_offer, version=1, max_discount_pct=Decimal("30.00"),
                                              minimum_price=(price * Decimal("0.7")).quantize(Decimal("0.01")),
                                              authorized_by=owners[store_name], starts_at=timezone.now())
        self.stdout.write(self.style.SUCCESS("Demo cargada: 3 tiendas, 12 productos y 15 lotes"))

    def _receive(self, lot, qty, owner, key):
        movement = InventoryMovement.objects.create(store=lot.product.store, actor=owner,
                                                    kind=InventoryMovement.Kind.INBOUND,
                                                    state=InventoryMovement.State.CONFIRMED,
                                                    confirmed_at=timezone.now(),
                                                    idempotency_key=uuid.uuid5(uuid.NAMESPACE_URL, key),
                                                    request_hash="0" * 64)
        MovementLine.objects.create(movement=movement, lot=lot, physical_delta=qty)
        lot.physical_qty = qty
        lot.save(update_fields=["physical_qty", "updated_at"])
