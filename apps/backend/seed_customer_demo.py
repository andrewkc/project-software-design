"""Optional local-only demo data. Run after database.sql and seed.sql.

Requires BODESMART_DEMO_SEED=1; credentials are generated into an ignored file.
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
from database import ensure_schema, next_profile_id
from security import hash_password

ROOT = Path(__file__).resolve().parents[2]
CREDENTIALS = ROOT / ".demo-credentials.json"


def main():
    if os.getenv("BODESMART_DEMO_SEED") != "1":
        raise SystemExit("Establece BODESMART_DEMO_SEED=1 para crear datos locales")
    ensure_schema()
    credentials = json.loads(CREDENTIALS.read_text(encoding="utf-8")) if CREDENTIALS.exists() else {
        "owner": {"correo": "dueno.demo@bodesmart.local", "password": secrets.token_urlsafe(14)},
        "employee": {"correo": "empleado.demo@bodesmart.local", "password": secrets.token_urlsafe(14)},
        "customer": {"correo": "cliente.demo@bodesmart.local", "password": secrets.token_urlsafe(14)},
    }
    stores = [
        ("Bodega San Martín", "Av. San Martín 245, Lima"),
        ("Mercado Verde", "Av. Los Olivos 110, Lima"),
        ("Despensa Cercana", "Jr. Las Flores 72, Lima"),
    ]
    samples = [
        ("Yogurt natural", "Lácteos", "🥛", Decimal("4.50"), 9, 12),
        ("Manzana roja", "Frutas", "🍎", Decimal("3.20"), 12, 18),
        ("Pan de molde", "Panadería", "🍞", Decimal("6.80"), 8, 10),
        ("Queso fresco", "Lácteos", "🧀", Decimal("8.50"), 10, 14),
    ]
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        store_ids = []
        for name, address in stores:
            row = conn.execute("SELECT id FROM Bodega WHERE nombre = %s ORDER BY id LIMIT 1", (name,)).fetchone()
            if row:
                store_id = row["id"]
                conn.execute("UPDATE Bodega SET direccion = %s WHERE id = %s AND direccion = ''", (address, store_id))
            else:
                store_id = conn.execute("INSERT INTO Bodega(nombre,direccion) VALUES (%s,%s) RETURNING id", (name, address)).fetchone()["id"]
            store_ids.append(store_id)
        store_factors = [Decimal("1.00"), Decimal("0.90"), Decimal("1.15")]
        for store_id, factor in zip(store_ids, store_factors):
            for name, category, icon, price, days, stock in samples:
                store_price = (price * factor).quantize(Decimal("0.01"))
                offer_price = (store_price * Decimal("0.80")).quantize(Decimal("0.01"))
                row = conn.execute("""SELECT p.id FROM Producto p JOIN ProductosBodega pb ON pb.id_producto = p.id
                                      WHERE pb.id_bodega = %s AND p.nombre = %s LIMIT 1""", (store_id, name)).fetchone()
                if row:
                    product_id = row["id"]
                    # Existing stock is respected. Expired old seed rows are replaced only in this local demo.
                    conn.execute("""UPDATE ProductosBodega SET fecha_vencimiento = %s, precio_venta = %s,
                                  stock = GREATEST(stock, %s), estado = 'activo'
                                  WHERE id_bodega = %s AND id_producto = %s AND
                                  (fecha_vencimiento IS NULL OR fecha_vencimiento <= CURRENT_DATE)""",
                                 (date.today() + timedelta(days=days), store_price, stock, store_id, product_id))
                    # Update only untouched demo prices; leave owner edits intact.
                    conn.execute("""UPDATE ProductosBodega SET precio_venta = %s
                                    WHERE id_bodega = %s AND id_producto = %s AND precio_venta = %s""",
                                 (store_price, store_id, product_id, price))
                else:
                    product_id = conn.execute("""INSERT INTO Producto(nombre,categoria,icono,unidad_medida)
                                                 VALUES (%s,%s,%s,'unid.') RETURNING id""",
                                              (name, category, icon)).fetchone()["id"]
                    conn.execute("""INSERT INTO ProductosBodega(id_producto,id_bodega,stock,precio_venta,fecha_vencimiento,estado)
                                    VALUES (%s,%s,%s,%s,%s,'activo')""",
                                 (product_id, store_id, stock, store_price, date.today() + timedelta(days=days)))
                if not conn.execute("SELECT 1 FROM Oferta WHERE id_producto = %s AND id_bodega = %s", (product_id, store_id)).fetchone():
                    conn.execute("""INSERT INTO Oferta(id_producto,id_bodega,precio_original,precio_oferta,fecha_inicio,fecha_fin,estado)
                                    VALUES (%s,%s,%s,%s,now() - interval '1 day',now() + interval '30 days','activo')""",
                                 (product_id, store_id, store_price, offer_price))
                else:
                    conn.execute("""UPDATE Oferta SET precio_original = %s, precio_oferta = %s
                                    WHERE id_producto = %s AND id_bodega = %s
                                      AND precio_original = %s AND precio_oferta = %s""",
                                 (store_price, offer_price, product_id, store_id, price,
                                  (price * Decimal("0.80")).quantize(Decimal("0.01"))))
        owner = conn.execute("SELECT id FROM Jefe WHERE lower(correo) = %s", (credentials["owner"]["correo"],)).fetchone()
        if not owner:
            owner_id = next_profile_id(conn)
            conn.execute("""INSERT INTO Jefe(id,nombres,apellidos,correo,password,id_bodega)
                            VALUES (%s,'Dueño','Demo',%s,%s,%s)""",
                         (owner_id, credentials["owner"]["correo"], hash_password(credentials["owner"]["password"]), store_ids[0]))
        else:
            owner_id = owner["id"]
            conn.execute("UPDATE Jefe SET password = %s WHERE id = %s", (hash_password(credentials["owner"]["password"]), owner_id))
        employee = conn.execute("SELECT id FROM Empleado WHERE lower(correo) = %s", (credentials["employee"]["correo"],)).fetchone()
        if not employee:
            conn.execute("""INSERT INTO Empleado(id,nombres,apellidos,correo,password,id_jefe,estado)
                            VALUES (%s,'Empleado','Demo',%s,%s,%s,'activo')""",
                         (next_profile_id(conn), credentials["employee"]["correo"], hash_password(credentials["employee"]["password"]), owner_id))
        else:
            conn.execute("UPDATE Empleado SET password = %s, estado = 'activo' WHERE id = %s",
                         (hash_password(credentials["employee"]["password"]), employee["id"]))
        buyer = conn.execute("SELECT id FROM Cliente WHERE lower(correo) = %s", (credentials["customer"]["correo"],)).fetchone()
        if not buyer:
            conn.execute("""INSERT INTO Cliente(nombres,apellidos,correo,password)
                            VALUES ('Cliente','Demo',%s,%s)""",
                         (credentials["customer"]["correo"], hash_password(credentials["customer"]["password"])))
        else:
            conn.execute("UPDATE Cliente SET password = %s, estado = 'activo' WHERE id = %s",
                         (hash_password(credentials["customer"]["password"]), buyer["id"]))
    CREDENTIALS.write_text(json.dumps(credentials, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Demo lista: {len(stores)} bodegas; credenciales en {CREDENTIALS}")


if __name__ == "__main__":
    main()
