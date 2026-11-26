"""Optional local-only catalog data for customer-web.

Run once after database.sql and seed.sql:

    BODESMART_DEMO_SEED=1 python apps/backend/seed_customer_demo.py

It is deliberately additive and idempotent: it never changes existing manager
or employee accounts, never overwrites a password, price or offer created by
the owner, and never resurrects expired or deteriorated stock. The generated
20% discount is owned by ensure_storefront_offers(), so any offer seeded here
is refreshed from ProductosBodega on the next catalog read. Credentials for
the new demo buyer are written to the ignored .demo-credentials.json file.
"""

import json
import os
import secrets
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from config import DSN
from database import ensure_schema
from security import hash_password

ROOT = Path(__file__).resolve().parents[2]
CREDENTIALS = ROOT / ".demo-credentials.json"
CUSTOMER_EMAIL = "cliente.tienda@bodesmart.local"

# Demo-only addresses. They are derived data for the local academic prototype,
# not requirements gathered from the interviews.
STORES = (
    ("Bodega San Martín", "Av. San Martín 245, Lima"),
    ("Mercado Verde", "Av. Los Olivos 110, Lima"),
    ("Despensa Cercana", "Jr. Las Flores 72, Lima"),
)

# Only products that are active and have a future expiry in seed.sql. The seed
# below never invents products outside the committed catalog.
OFFER_PRODUCTS = (
    ("Arroz extra", Decimal("0.80")),
    ("Galletas de soda", Decimal("0.85")),
    ("Atún en lata", Decimal("0.80")),
    ("Leche chocolatada", Decimal("0.85")),
    ("Yogurt de fresa", Decimal("0.80")),
    ("Manzana roja", Decimal("0.85")),
    ("Fideos largos", Decimal("0.80")),
    ("Jugo de naranja", Decimal("0.85")),
)


def _credentials():
    data = json.loads(CREDENTIALS.read_text(encoding="utf-8")) if CREDENTIALS.exists() else {}
    entry = data.get("store_customer")
    if not entry:
        entry = {"correo": CUSTOMER_EMAIL, "password": secrets.token_urlsafe(14)}
        data["store_customer"] = entry
    return data, entry


def main():
    if os.getenv("BODESMART_DEMO_SEED") != "1":
        raise SystemExit("Establece BODESMART_DEMO_SEED=1 para crear datos locales")
    ensure_schema()
    data, entry = _credentials()

    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        store_ids = []
        for name, address in STORES:
            row = conn.execute(
                "SELECT id FROM Bodega WHERE nombre = %s ORDER BY id LIMIT 1", (name,)
            ).fetchone()
            created = row is None
            if created:
                store_id = conn.execute(
                    "INSERT INTO Bodega(nombre, direccion) VALUES (%s, %s) RETURNING id",
                    (name, address),
                ).fetchone()["id"]
            else:
                store_id = row["id"]
                # Fill only an empty address; an owner-entered address is kept.
                conn.execute(
                    """UPDATE Bodega SET direccion = %s
                       WHERE id = %s AND (direccion IS NULL OR btrim(direccion) = '')""",
                    (address, store_id),
                )
            store_ids.append((store_id, created))

        for index, (store_id, created) in enumerate(store_ids):
            for offset, (name, discount) in enumerate(OFFER_PRODUCTS):
                product = conn.execute(
                    "SELECT id FROM Producto WHERE nombre = %s ORDER BY id LIMIT 1", (name,)
                ).fetchone()
                if not product:
                    continue
                product_id = product["id"]
                warehouse = conn.execute(
                    """SELECT stock, precio_venta, fecha_vencimiento, estado
                       FROM ProductosBodega WHERE id_producto = %s AND id_bodega = %s""",
                    (product_id, store_id),
                ).fetchone()
                if warehouse:
                    if (warehouse["estado"] != "activo"
                            or (warehouse["fecha_vencimiento"] is not None
                                and warehouse["fecha_vencimiento"] <= date.today())):
                        continue
                    price = Decimal(str(warehouse["precio_venta"]))
                elif created:
                    base = conn.execute(
                        """SELECT precio_venta FROM ProductosBodega
                           WHERE id_producto = %s AND id_bodega = 1""", (product_id,)
                    ).fetchone()
                    if not base:
                        continue
                    price = Decimal(str(base["precio_venta"]))
                    conn.execute(
                        """INSERT INTO ProductosBodega(
                               id_producto, id_bodega, stock, precio_venta,
                               fecha_vencimiento, estado, creado_por)
                           VALUES (%s, %s, %s, %s, %s, 'activo', NULL)""",
                        (product_id, store_id, 10, price,
                         date.today() + timedelta(days=45 + offset)),
                    )
                else:
                    # Do not add inventory to a pre-existing store from a demo script.
                    continue
                if price <= 0:
                    continue
                if conn.execute(
                    "SELECT 1 FROM Oferta WHERE id_producto = %s AND id_bodega = %s",
                    (product_id, store_id),
                ).fetchone():
                    continue
                offer_price = (price * discount).quantize(Decimal("0.01"))
                conn.execute(
                    """INSERT INTO Oferta(id_producto, id_bodega, precio_original,
                                          precio_oferta, fecha_inicio, fecha_fin, estado)
                       VALUES (%s, %s, %s, %s, now() - interval '1 day',
                               now() + interval '30 days', 'activo')""",
                    (product_id, store_id, price, offer_price),
                )

        # A dedicated buyer: never reuse or change cliente.demo@bodesmart.local,
        # which is owned by sales_service.ensure_demo_sales().
        buyer = conn.execute(
            "SELECT id FROM Cliente WHERE lower(correo) = lower(%s)", (entry["correo"],)
        ).fetchone()
        if not buyer:
            conn.execute(
                """INSERT INTO Cliente(nombres, apellidos, correo, password, estado)
                   VALUES ('Cliente', 'Tienda', %s, %s, 'activo')""",
                (entry["correo"], hash_password(entry["password"])),
            )

    CREDENTIALS.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Demo de cliente lista; credenciales en {CREDENTIALS}")


if __name__ == "__main__":
    main()
