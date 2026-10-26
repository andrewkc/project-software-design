from datetime import timedelta

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Sum

from core.models import InventoryMovement, Lot, MovementLine, Offer, Product, Store, StorePricingPolicy, User


pytestmark = pytest.mark.django_db


def test_seed_requires_nontrivial_password(monkeypatch):
    monkeypatch.delenv("DESSOF_DEMO_PASSWORD", raising=False)
    with pytest.raises(CommandError):
        call_command("seed_demo")
    monkeypatch.setenv("DESSOF_DEMO_PASSWORD", "short")
    with pytest.raises(CommandError):
        call_command("seed_demo")
    assert Store.objects.count() == 0


def test_seed_rejects_nonempty_database(monkeypatch, store):
    monkeypatch.setenv("DESSOF_DEMO_PASSWORD", "StrongDemoPass123!")
    with pytest.raises(CommandError):
        call_command("seed_demo")
    assert Store.objects.count() == 1


def test_seed_populates_three_independent_stores(monkeypatch):
    monkeypatch.setenv("DESSOF_DEMO_PASSWORD", "StrongDemoPass123!")
    call_command("seed_demo", verbosity=0)
    assert Store.objects.count() == 3
    assert Product.objects.count() == 12
    assert Lot.objects.count() == 15
    assert Offer.objects.count() == 15
    assert User.objects.filter(role=User.Role.OWNER).count() == 3
    assert User.objects.filter(role=User.Role.EMPLOYEE).count() == 3
    assert User.objects.filter(role=User.Role.CUSTOMER).count() == 2
    assert User.objects.filter(role=User.Role.ADMIN).count() == 1
    assert all(StorePricingPolicy.objects.get(store=s).mode == StorePricingPolicy.Mode.REVIEW for s in Store.objects.all())
    assert all(l.expiry_date - l.received_date >= timedelta(days=7) for l in Lot.objects.all())
    assert all(l.physical_qty == l.received_qty and l.reserved_qty == 0 for l in Lot.objects.all())
    assert InventoryMovement.objects.filter(kind=InventoryMovement.Kind.INBOUND, state="CONFIRMED").count() == 15
    assert MovementLine.objects.aggregate(total=Sum("physical_delta"))["total"] == Lot.objects.aggregate(total=Sum("physical_qty"))["total"]
    assert Product.objects.filter(lots__code__endswith="02").distinct().count() == 3
    with pytest.raises(CommandError):
        call_command("seed_demo", verbosity=0)
    assert Store.objects.count() == 3
