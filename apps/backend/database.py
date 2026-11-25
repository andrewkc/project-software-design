from typing import Optional

import psycopg
from psycopg.rows import dict_row

from config import DSN
from security import hash_password


def ensure_schema():
    # These fields are needed by the role/lock rules but are not in database.sql.
    statements = [
        "ALTER TABLE Empleado ADD COLUMN IF NOT EXISTS estado VARCHAR(20) NOT NULL DEFAULT 'activo'",
        "ALTER TABLE ProductosBodega ADD COLUMN IF NOT EXISTS creado_por INT",
        "ALTER TABLE ProductosBodega ADD COLUMN IF NOT EXISTS bloqueado BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE ProductosBodega ADD COLUMN IF NOT EXISTS bloqueado_por INT",
        # Jefe and Empleado have separate SERIAL sequences, so ids can collide.
        # New profiles share this one; the seeded jefe keeps id 1.
        "CREATE SEQUENCE IF NOT EXISTS bodesmart_profile_id START 1000",
    ]
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        for statement in statements:
            conn.execute(statement)
        # One-time migration: the original seed stored one password in plain
        # text. Rehash any such row so every stored password is a bcrypt hash.
        for table in ("Jefe", "Empleado"):
            rows = conn.execute(f"SELECT id, password FROM {table}").fetchall()
            for row in rows:
                stored = row["password"]
                if not stored.startswith(("$2a$", "$2b$", "$2y$")):
                    conn.execute(
                        f"UPDATE {table} SET password = %s WHERE id = %s",
                        (hash_password(stored), row["id"]),
                    )


def profile_response(row: dict, rol: str) -> dict:
    nombres = row.get("nombres") or ""
    apellidos = row.get("apellidos") or ""
    return {
        "id": row["id"],
        "rol": rol,
        "nombres": nombres,
        "apellidos": apellidos,
        "nombre": f"{nombres} {apellidos}".strip(),
        "correo": row["correo"],
        "bodegaNombre": row.get("nombre_bodega") or "",
        "activo": row.get("estado", "activo") == "activo",
    }


def product_response(row: dict) -> dict:
    return {
        "id": row["id"],
        "id_producto": row["id"],
        "nombre": row["nombre"],
        "categoria": row.get("categoria") or "",
        "icono": row.get("icono") or "📦",
        "stock": row["stock"],
        "unidad_medida": row.get("unidad_medida") or "unid.",
        "precio_venta": float(row["precio_venta"]),
        "fecha_vencimiento": row["fecha_vencimiento"].isoformat() if row.get("fecha_vencimiento") else None,
        "estado": row.get("estado") or "activo",
        "creado_por": row.get("creado_por"),
        "bloqueado": bool(row.get("bloqueado")),
        "bloqueado_por": row.get("bloqueado_por"),
    }


def fetch_profile(conn, who: dict) -> dict:
    if who["rol"] == "jefe":
        row = conn.execute(
            """SELECT j.*, b.nombre AS nombre_bodega
               FROM Jefe j JOIN Bodega b ON b.id = j.id_bodega
               WHERE j.id = %s""",
            (who["id"],),
        ).fetchone()
        return profile_response(row, "jefe") if row else None

    row = conn.execute(
        """SELECT e.*, b.nombre AS nombre_bodega
           FROM Empleado e
           JOIN Jefe j ON j.id = e.id_jefe
           JOIN Bodega b ON b.id = j.id_bodega
           WHERE e.id = %s""",
        (who["id"],),
    ).fetchone()
    return profile_response(row, "empleado") if row else None


def bodega_id_for(conn, who: dict) -> Optional[int]:
    if who["rol"] == "jefe":
        row = conn.execute("SELECT id_bodega FROM Jefe WHERE id = %s", (who["id"],)).fetchone()
    else:
        row = conn.execute(
            """SELECT j.id_bodega FROM Empleado e
               JOIN Jefe j ON j.id = e.id_jefe
               WHERE e.id = %s AND COALESCE(e.estado, 'activo') = 'activo'""",
            (who["id"],),
        ).fetchone()
    return row["id_bodega"] if row else None


def fetch_product(conn, bodega_id: int, product_id: int) -> Optional[dict]:
    row = conn.execute(
        """SELECT p.id, p.nombre, p.categoria, p.icono, p.unidad_medida,
                  pb.stock, pb.precio_venta, pb.fecha_vencimiento, pb.estado,
                  pb.creado_por, pb.bloqueado, pb.bloqueado_por
           FROM Producto p
           JOIN ProductosBodega pb ON pb.id_producto = p.id
           WHERE pb.id_bodega = %s AND p.id = %s""",
        (bodega_id, product_id),
    ).fetchone()
    return row


def email_exists(conn, correo: str) -> bool:
    for table in ("Jefe", "Empleado"):
        row = conn.execute(
            f"SELECT id FROM {table} WHERE lower(correo) = lower(%s)", (correo,)
        ).fetchone()
        if row:
            return True
    return False


def normalize_date(value):
    if value is None or value == "":
        return None
    return value


def next_profile_id(conn) -> int:
    return conn.execute("SELECT nextval('bodesmart_profile_id')").fetchone()["nextval"]
