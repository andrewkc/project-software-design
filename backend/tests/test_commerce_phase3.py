import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import close_old_connections
from django.utils import timezone

from core import commerce, services
from core.models import InventoryMovement, Lot, Offer, Order, PaymentAttempt, Reservation, User


pytestmark = pytest.mark.django_db


def request(offer, qty=250, idem=None):
    return {"idempotency_key": idem or str(uuid.uuid4()),
            "lines": [{"offer_id": str(offer.id), "base_quantity": qty}]}


def fails(code, func, *args):
    with pytest.raises(services.DomainError) as exc:
        func(*args)
    assert exc.value.code == code


def test_catalog_only_shows_sellable_published_offers(offer, owner):
    assert [item.id for item in commerce.public_offers()] == [offer.id]
    offer.state = Offer.State.PAUSED
    offer.save(update_fields=["state"])
    assert commerce.public_offers() == []


def test_catalog_hides_reserved_out_offer(offer, lot):
    lot.reserved_qty = 1250
    lot.save(update_fields=["reserved_qty"])
    assert commerce.public_offers() == []


def test_customer_reserves_stock_and_price_snapshot(customer, offer, lot):
    order = commerce.create_order(customer, request(offer, 500))
    lot.refresh_from_db()
    assert order.state == Order.State.PENDING and order.total == Decimal("18.00")
    assert (lot.physical_qty, lot.reserved_qty, lot.available_qty) == (1250, 500, 750)
    assert order.lines.get().step_price_snapshot == Decimal("9.00")
    assert order.lines.get().reservation.state == Reservation.State.ACTIVE


def test_order_retry_is_idempotent(customer, offer, lot):
    data = request(offer)
    first = commerce.create_order(customer, data)
    second = commerce.create_order(customer, data)
    lot.refresh_from_db()
    assert first.id == second.id and lot.reserved_qty == 250 and Order.objects.count() == 1


def test_order_retry_with_changed_body_conflicts(customer, offer, lot):
    data = request(offer)
    commerce.create_order(customer, data)
    fails("IDEMPOTENCY_CONFLICT", commerce.create_order, customer,
          request(offer, 500, data["idempotency_key"]))
    lot.refresh_from_db()
    assert lot.reserved_qty == 250


def test_other_customer_cannot_reuse_key_or_see_order(customer, offer):
    order = commerce.create_order(customer, request(offer))
    other = User.objects.create_user(email="other@demo.test", password="SecurePass123!",
                                     name="Otra", role=User.Role.CUSTOMER)
    fails("IDEMPOTENCY_CONFLICT", commerce.create_order, other,
          request(offer, 250, str(order.idempotency_key)))
    fails("NOT_FOUND", commerce.get_order, other, order.id)


@pytest.mark.parametrize("qty,code", [(0, "INVALID_QUANTITY"), (251, "INVALID_STEP"),
                                     (1500, "INSUFFICIENT_STOCK")])
def test_bad_order_leaves_no_reservation(customer, offer, lot, qty, code):
    fails(code, commerce.create_order, customer, request(offer, qty))
    lot.refresh_from_db()
    assert lot.reserved_qty == 0 and not Order.objects.exists()


def test_duplicate_line_rejected(customer, offer):
    data = request(offer)
    data["lines"].append(data["lines"][0].copy())
    fails("DUPLICATE_OFFER", commerce.create_order, customer, data)


def test_mixed_store_order_rolls_back(customer, offer, other_store, lot):
    from core.models import Product
    p = Product.objects.create(store=other_store, code="B", name="B", category="X", unit="UNIT",
                               sale_step=1, reference_price=Decimal("2"), storage_conditions="X")
    other_lot = Lot.objects.create(product=p, code="B1", received_date=timezone.localdate(),
        expiry_date=timezone.localdate() + timedelta(days=8),
        sales_close_at=timezone.now() + timedelta(days=7), total_cost=Decimal("1"),
        received_qty=10, physical_qty=10)
    other_offer = Offer.objects.create(lot=other_lot, state=Offer.State.PUBLISHED,
                                       original_price=Decimal("2"), current_price=Decimal("2"))
    data = request(offer)
    data["lines"].append({"offer_id": str(other_offer.id), "base_quantity": 1})
    fails("MIXED_STORES", commerce.create_order, customer, data)
    lot.refresh_from_db()
    other_lot.refresh_from_db()
    assert lot.reserved_qty == other_lot.reserved_qty == 0


def test_owner_cannot_create_customer_order(owner, offer):
    fails("FORBIDDEN", commerce.create_order, owner, request(offer))


def test_simulated_approval_decrements_once_and_keeps_snapshot(customer, offer, lot):
    order = commerce.create_order(customer, request(offer, 500))
    offer.current_price = Decimal("8")
    offer.save(update_fields=["current_price"])
    first = commerce.simulate_payment(customer, order.id, "APPROVE")
    second = commerce.simulate_payment(customer, order.id, "APPROVE")
    lot.refresh_from_db()
    assert first.id == second.id and first.state == Order.State.PAID
    assert (lot.physical_qty, lot.reserved_qty) == (750, 0)
    assert InventoryMovement.objects.get(order=order).lines.get().amount == Decimal("18.00")
    assert PaymentAttempt.objects.filter(order=order).count() == 1


def test_simulated_rejection_releases_stock(customer, offer, lot):
    order = commerce.create_order(customer, request(offer, 500))
    result = commerce.simulate_payment(customer, order.id, "REJECT")
    lot.refresh_from_db()
    assert result.state == Order.State.FAILED and (lot.physical_qty, lot.reserved_qty) == (1250, 0)
    assert not InventoryMovement.objects.filter(order=order).exists()
    fails("ORDER_FINALIZED", commerce.simulate_payment, customer, order.id, "APPROVE")


def test_expired_order_releases_stock_and_cannot_approve(customer, offer, lot):
    order = commerce.create_order(customer, request(offer))
    Order.objects.filter(pk=order.pk).update(reservation_until=timezone.now() - timedelta(seconds=1))
    result = commerce.simulate_payment(customer, order.id, "APPROVE")
    lot.refresh_from_db()
    assert result.state == Order.State.EXPIRED and lot.reserved_qty == 0
    assert not PaymentAttempt.objects.filter(order=order).exists()


def test_local_sale_cannot_consume_reserved_stock(customer, employee, product, offer, lot):
    commerce.create_order(customer, request(offer, 1000))
    fails("INSUFFICIENT_STOCK", services.sell_local, employee,
          {"product_id": str(product.id), "quantity": 500, "idempotency_key": str(uuid.uuid4())})
    lot.refresh_from_db()
    assert lot.physical_qty == 1250 and lot.reserved_qty == 1000


def test_expiration_worker_releases_due_reservations(customer, offer, lot):
    order = commerce.create_order(customer, request(offer, 500))
    Order.objects.filter(pk=order.pk).update(reservation_until=timezone.now() - timedelta(seconds=1))
    commerce.expire_due_orders()
    order.refresh_from_db()
    lot.refresh_from_db()
    assert order.state == Order.State.EXPIRED
    assert lot.reserved_qty == 0 and order.lines.get().reservation.state == Reservation.State.RELEASED


@pytest.mark.django_db(transaction=True)
def test_competing_customers_cannot_reserve_more_than_available():
    from core.models import Product, Store
    store = Store.objects.create(name="Concurrencia web", address="Calle")
    product = Product.objects.create(store=store, code="C", name="C", category="X", unit="UNIT",
                                     sale_step=1, reference_price=Decimal("2"), storage_conditions="X")
    lot = Lot.objects.create(product=product, code="C1", received_date=timezone.localdate(),
        expiry_date=timezone.localdate() + timedelta(days=8),
        sales_close_at=timezone.now() + timedelta(days=7), total_cost=Decimal("1"),
        received_qty=1, physical_qty=1)
    offer = Offer.objects.create(lot=lot, state=Offer.State.PUBLISHED,
                                 original_price=Decimal("2"), current_price=Decimal("2"))
    buyers = [User.objects.create_user(email=f"buyer{i}@example.test", password="SecurePass123!",
               name=f"Buyer {i}", role=User.Role.CUSTOMER) for i in range(2)]

    def reserve(buyer):
        close_old_connections()
        try:
            return commerce.create_order(buyer, request(offer, 1)).id
        except services.DomainError as error:
            return error.code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(reserve, buyers))
    lot.refresh_from_db()
    assert sum(isinstance(outcome, uuid.UUID) for outcome in outcomes) == 1
    assert "INSUFFICIENT_STOCK" in outcomes
    assert lot.reserved_qty == 1 and lot.physical_qty == 1 and Order.objects.count() == 1
