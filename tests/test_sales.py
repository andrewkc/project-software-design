"""Static and unit checks for VENTAS-01 (sales history + atomic purchase).

Run from the repository root with the backend venv:
    apps\\backend\\.venv\\Scripts\\python -m pytest tests/test_sales.py -v

No server, API key or PostgreSQL instance is required: the transaction is
exercised through a small in-memory connection double.
"""

import sys
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "backend"
FRONTEND_SRC = ROOT / "apps" / "operations-web" / "src"

sys.path.insert(0, str(BACKEND))
import sales_service  # noqa: E402


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Static contract checks
# ---------------------------------------------------------------------------

def test_schema_contains_reference_purchase_tables():
    sql = read("apps/database/database.sql")
    for token in (
        "CREATE TABLE Compra (",
        "CREATE TABLE DetalleCompra (",
        "CREATE TABLE Pago (",
        "CREATE TABLE ReservaCompra (",
        "idempotency_key UUID UNIQUE",
        "request_hash VARCHAR(64)",
        "fecha_pago TIMESTAMPTZ",
        "id_oferta INT REFERENCES Oferta(id)",
        "ix_reserva_activa",
    ):
        assert token in sql, token
    assert "CREATE TABLE Movimiento" not in sql
    assert "CREATE TABLE DetalleMovimiento" not in sql


def test_migrations_are_idempotent_for_existing_database():
    code = read("apps/backend/database.py")
    for token in (
        "ALTER TABLE Compra ADD COLUMN IF NOT EXISTS idempotency_key UUID UNIQUE",
        "ALTER TABLE Compra ADD COLUMN IF NOT EXISTS request_hash VARCHAR(64)",
        "ALTER TABLE Compra ADD COLUMN IF NOT EXISTS fecha_pago TIMESTAMPTZ",
        "ALTER TABLE DetalleCompra ADD COLUMN IF NOT EXISTS id_oferta INT REFERENCES Oferta(id)",
        "CREATE TABLE IF NOT EXISTS ReservaCompra",
    ):
        assert token in code, token
    assert "ensure_demo_sales(conn)" in code


def test_only_paid_purchases_are_exposed():
    router = read("apps/backend/routers/sales.py")
    service = read("apps/backend/sales_service.py")
    assert "c.estado = 'pagado'" in router
    assert "'pagado'" in service
    for status in ("pendiente", "expirado", "rechazado", "pago_en_revision"):
        assert f"c.estado = '{status}'" not in router
    assert "bodega_id_for(conn, who)" in router


def test_atomic_decrement_and_lock_are_present():
    service = read("apps/backend/sales_service.py")
    assert "FOR UPDATE OF pb" in service
    assert "UPDATE ProductosBodega SET stock = stock - %s" in service
    assert "WHERE id_producto = %s AND id_bodega = %s AND stock >= %s" in service
    assert "RETURNING stock" in service
    assert "pg_advisory_xact_lock" in service
    assert "INSERT INTO ReservaCompra" in service
    assert "'consumida'" in service


def test_demo_sales_are_keyed_and_guarded():
    assert len(sales_service.DEMO_SALES) == 3
    keys = [key for key, _ in sales_service.DEMO_SALES]
    assert len(set(keys)) == 3
    assert all(isinstance(key, type(keys[0])) for key in keys)
    service = read("apps/backend/sales_service.py")
    assert "SELECT 1 FROM Compra WHERE idempotency_key = %s" in service
    assert "with conn.transaction():" in service


def test_navigation_is_visible_to_both_roles():
    data = read("apps/operations-web/src/data/demoData.js")
    entries = [line.strip() for line in data.splitlines() if 'id: "sales"' in line]
    assert len(entries) == 2, entries
    for entry in entries:
        assert 'label: "Ventas"' in entry
        assert "jefeOnly" not in entry
        assert "empleadoOnly" not in entry


def test_frontend_exposes_sales_contract():
    api = read("apps/operations-web/src/lib/api.js")
    assert 'listSales: () => request("/sales")' in api
    assert 'createSale: (payload) => request("/sales"' in api
    app = read("apps/operations-web/src/App.jsx")
    assert 'activeTab === "sales"' in app
    assert "const refreshData = useCallback" in app  # ventas y stock se recargan
    assert 'window.addEventListener("focus", onFocus)' in app
    assert "window.setInterval(() =>" in app
    assert app.count("onRefresh={refreshData}") == 2  # ventas e inventario
    page = read("apps/operations-web/src/features/sales/SalesPage.jsx")
    assert "Compras pagadas" in page
    assert "Aún no hay compras pagadas" in page
    assert "Actualizar" in page


# ---------------------------------------------------------------------------
# In-memory transaction double
# ---------------------------------------------------------------------------

class FakeCursor:
    def __init__(self, rows):
        self._rows = list(rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class FakeConn:
    """Minimal psycopg double that only understands sales_service queries."""

    def __init__(self, products, client_id=7, client_active=True):
        self.products = products
        self.client_id = client_id
        self.client_active = client_active
        self.purchases = {}
        self.lines = []
        self.reservas = []
        self.pagos = []
        self.next_id = 1
        self.stock_updates = 0

    @contextmanager
    def transaction(self):
        yield self

    def execute(self, sql, params=None):
        query = " ".join(sql.split())
        params = params or ()

        if "pg_advisory_xact_lock" in query:
            return FakeCursor([])
        if "UPDATE Compra SET estado = 'expirado'" in query:
            return FakeCursor([])
        if "UPDATE ReservaCompra SET estado = 'liberada'" in query:
            return FakeCursor([])
        if "SELECT id FROM Cliente WHERE id =" in query:
            rows = [{"id": self.client_id}] if self.client_active else []
            return FakeCursor(rows)
        if "SELECT now()::timestamp" in query:
            return FakeCursor([{
                "local_now": datetime(2026, 11, 26, 12, 0),
                "local_date": date(2026, 11, 26),
            }])
        if "FOR UPDATE OF pb" in query:
            product_id, bodega_id = params
            row = self.products.get((product_id, bodega_id))
            return FakeCursor([row] if row else [])
        if "FROM Oferta" in query:
            return FakeCursor([])
        if "INSERT INTO Compra(" in query:
            purchase_id = self.next_id
            self.next_id += 1
            row = {
                "id": purchase_id,
                "id_cliente": params[0],
                "id_bodega": params[1],
                "total": params[2],
                "estado": "pagado",
                "fecha_compra": datetime(2026, 11, 26, 12, 0),
                "fecha_pago": datetime(2026, 11, 26, 12, 0),
                "idempotency_key": params[3],
                "request_hash": params[4],
                "reserva_hasta": None,
            }
            self.purchases[purchase_id] = row
            return FakeCursor([{"id": purchase_id}])
        if "UPDATE ProductosBodega SET stock" in query:
            quantity, product_id, bodega_id, _ = params
            row = self.products.get((product_id, bodega_id))
            if row and row["stock"] >= quantity:
                row["stock"] -= quantity
                self.stock_updates += 1
                return FakeCursor([{"stock": row["stock"]}])
            return FakeCursor([])
        if "INSERT INTO DetalleCompra(" in query:
            self.lines.append(params)
            return FakeCursor([])
        if "INSERT INTO ReservaCompra(" in query:
            self.reservas.append(params)
            return FakeCursor([])
        if "INSERT INTO Pago(" in query:
            self.pagos.append(params)
            return FakeCursor([])
        if "SELECT * FROM Compra WHERE id =" in query:
            return FakeCursor([self.purchases[params[0]]])
        if "SELECT id, id_cliente, request_hash FROM Compra WHERE idempotency_key" in query:
            rows = [row for row in self.purchases.values() if row["idempotency_key"] == params[0]]
            return FakeCursor(rows)
        if "SELECT d.id, d.id_producto" in query:
            purchase_id = params[0]
            rows = []
            for index, line in enumerate(self.lines, start=1):
                if line[0] != purchase_id:
                    continue
                product = self.products.get((line[1], purchase_id * 0 + 1), {})
                rows.append({
                    "id": index,
                    "id_producto": line[1],
                    "id_oferta": line[2],
                    "cantidad": line[3],
                    "precio_unitario": line[4],
                    "subtotal": line[5],
                    "nombre": product.get("nombre", "Producto"),
                    "icono": product.get("icono", "📦"),
                    "unidad_medida": product.get("unidad_medida", "unid."),
                })
            return FakeCursor(rows)
        if "SELECT nombres, apellidos FROM Cliente" in query:
            return FakeCursor([{"nombres": "Cliente", "apellidos": "Demo"}])
        if "SELECT metodo_pago, estado FROM Pago" in query:
            return FakeCursor([{"metodo_pago": "LOCAL_SIMULATION", "estado": "aprobado"}])
        raise AssertionError(f"Unexpected SQL in fake connection: {query}")


def product_row(product_id, stock, price="4.50", expiry=None, estado="activo"):
    return {
        "id": product_id,
        "nombre": f"Producto {product_id}",
        "icono": "🍎",
        "unidad_medida": "kg",
        "stock": stock,
        "precio_venta": price,
        "fecha_vencimiento": expiry,
        "estado": estado,
    }


def test_paid_sale_decrements_stock_once_and_freezes_prices():
    conn = FakeConn({(13, 1): product_row(13, 14)})
    result = sales_service.create_paid_sale(
        conn, id_cliente=7, bodega_id=1,
        lineas=[{"id_producto": 13, "cantidad": 4}],
    )

    assert result["estado"] == "pagado"
    assert result["lineas"][0]["cantidad"] == 4
    assert result["lineas"][0]["precioUnitario"] == "4.50"
    assert conn.products[(13, 1)]["stock"] == 10
    assert conn.stock_updates == 1
    assert len(conn.purchases) == 1
    assert len(conn.lines) == 1
    assert len(conn.reservas) == 1
    assert conn.reservas[0][4] == "consumida"
    assert len(conn.pagos) == 1
    assert conn.pagos[0][1] == "LOCAL_SIMULATION"


def test_sale_over_available_stock_is_rejected_without_write():
    conn = FakeConn({(13, 1): product_row(13, 3)})
    with pytest.raises(HTTPException) as error:
        sales_service.create_paid_sale(
            conn, id_cliente=7, bodega_id=1,
            lineas=[{"id_producto": 13, "cantidad": 4}],
        )
    assert error.value.status_code == 409
    assert conn.purchases == {}
    assert conn.lines == []
    assert conn.stock_updates == 0


def test_expired_or_inactive_product_is_not_sold():
    for kwargs in (
        {"expiry": date(2026, 11, 20)},
        {"estado": "deteriorado"},
    ):
        conn = FakeConn({(13, 1): product_row(13, 10, **kwargs)})
        with pytest.raises(HTTPException) as error:
            sales_service.create_paid_sale(
                conn, id_cliente=7, bodega_id=1,
                lineas=[{"id_producto": 13, "cantidad": 1}],
            )
        assert error.value.status_code == 409
        assert conn.stock_updates == 0


def test_inactive_client_cannot_buy():
    conn = FakeConn({(13, 1): product_row(13, 10)}, client_active=False)
    with pytest.raises(HTTPException) as error:
        sales_service.create_paid_sale(
            conn, id_cliente=7, bodega_id=1,
            lineas=[{"id_producto": 13, "cantidad": 1}],
        )
    assert error.value.status_code == 404
    assert conn.stock_updates == 0


def test_idempotency_key_does_not_decrement_twice():
    key = "11111111-1111-4111-8111-111111111111"
    conn = FakeConn({(13, 1): product_row(13, 14)})
    payload = {"id_cliente": 7, "bodega_id": 1,
               "lineas": [{"id_producto": 13, "cantidad": 4}],
               "idempotency_key": key}
    first = sales_service.create_paid_sale(conn, **payload)
    second = sales_service.create_paid_sale(conn, **payload)

    assert second["id"] == first["id"]
    assert len(conn.purchases) == 1
    assert conn.stock_updates == 1
    assert conn.products[(13, 1)]["stock"] == 10


def test_idempotency_key_with_other_content_is_rejected():
    key = "11111111-1111-4111-8111-111111111111"
    conn = FakeConn({(13, 1): product_row(13, 14)})
    sales_service.create_paid_sale(
        conn, id_cliente=7, bodega_id=1,
        lineas=[{"id_producto": 13, "cantidad": 4}],
        idempotency_key=key,
    )
    with pytest.raises(HTTPException) as error:
        sales_service.create_paid_sale(
            conn, id_cliente=7, bodega_id=1,
            lineas=[{"id_producto": 13, "cantidad": 5}],
            idempotency_key=key,
        )
    assert error.value.status_code == 409
    assert conn.stock_updates == 1


def test_positive_integer_validation():
    assert sales_service.positive_int(3, "cantidad") == 3
    for invalid in (0, -1, True, 1.5, "2"):
        with pytest.raises(HTTPException) as error:
            sales_service.positive_int(invalid, "cantidad")
        assert error.value.status_code == 400
