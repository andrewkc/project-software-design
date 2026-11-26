from typing import Optional

import psycopg
from psycopg.rows import dict_row

from config import DSN
from sales_service import ensure_demo_sales
from security import hash_password

BASE_CATEGORIAS = (
    "Abarrotes", "Lácteos", "Frutas", "Bebidas", "Limpieza",
    "Snacks", "Conservas", "Cuidado personal", "Otros",
)

# Demo-only platform account. The seed inserts the same row with a readable
# password; ensure_schema() hashes it on startup, as it already does for jefes
# and employees. Replace these values in any real deployment.
DEMO_ADMIN_CORREO = "admin@bodesmart.local"
DEMO_ADMIN_PASSWORD = "Admin123456"


def ensure_demo_admin(conn):
    """Make the local admin usable on databases created before seed.sql had it."""
    conn.execute(
        """INSERT INTO Admin (nombres, apellidos, correo, password, estado)
           SELECT 'Admin', 'Plataforma', %s, %s, 'activo'
           WHERE NOT EXISTS (
               SELECT 1 FROM Admin WHERE lower(correo) = lower(%s)
           )""",
        (DEMO_ADMIN_CORREO, DEMO_ADMIN_PASSWORD, DEMO_ADMIN_CORREO),
    )


def ensure_schema():
    # These fields are needed by the role/lock rules but are not in database.sql.
    statements = [
        "ALTER TABLE Empleado ADD COLUMN IF NOT EXISTS estado VARCHAR(20) NOT NULL DEFAULT 'activo'",
        "ALTER TABLE Jefe ADD COLUMN IF NOT EXISTS estado VARCHAR(20) NOT NULL DEFAULT 'activo'",
        "CREATE TABLE IF NOT EXISTS Admin ("
        "id SERIAL PRIMARY KEY, "
        "nombres VARCHAR(100) NOT NULL, apellidos VARCHAR(100) NOT NULL, "
        "correo VARCHAR(150) UNIQUE NOT NULL, password VARCHAR(255) NOT NULL, "
        "estado VARCHAR(20) NOT NULL DEFAULT 'activo', "
        "fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "ALTER TABLE Admin ADD COLUMN IF NOT EXISTS estado VARCHAR(20) NOT NULL DEFAULT 'activo'",
        "ALTER TABLE Admin ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE Admin ADD COLUMN IF NOT EXISTS ultimo_acceso TIMESTAMPTZ",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_admin_correo_ci ON Admin (lower(correo))",
        "ALTER TABLE ProductosBodega ADD COLUMN IF NOT EXISTS creado_por INT",
        "ALTER TABLE ProductosBodega ADD COLUMN IF NOT EXISTS bloqueado BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE ProductosBodega ADD COLUMN IF NOT EXISTS bloqueado_por INT",
        "CREATE TABLE IF NOT EXISTS Categoria ("
        "nombre VARCHAR(100) PRIMARY KEY, "
        "fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        # Migrate categories already stored on products into the new catalog.
        "INSERT INTO Categoria (nombre) SELECT DISTINCT ON (clave) nombre "
        "FROM (SELECT btrim(categoria) AS nombre, lower(btrim(categoria)) AS clave "
        "FROM Producto WHERE categoria IS NOT NULL AND btrim(categoria) <> '') AS cats "
        "ORDER BY clave, nombre ON CONFLICT DO NOTHING",
        # Jefe and Empleado have separate SERIAL sequences, so ids can collide.
        # New profiles share this one; the seeded jefe keeps id 1.
        "CREATE SEQUENCE IF NOT EXISTS bodesmart_profile_id START 1000",
        # Purchase tables follow the checkout contract used by customer-web.
        "ALTER TABLE Oferta ADD COLUMN IF NOT EXISTS id_bodega INT REFERENCES Bodega(id)",
        "ALTER TABLE Oferta ADD COLUMN IF NOT EXISTS precio_original DECIMAL(10,2)",
        "ALTER TABLE Compra ADD COLUMN IF NOT EXISTS reserva_hasta TIMESTAMPTZ",
        "ALTER TABLE Compra ADD COLUMN IF NOT EXISTS idempotency_key UUID UNIQUE",
        "ALTER TABLE Compra ADD COLUMN IF NOT EXISTS request_hash VARCHAR(64)",
        "ALTER TABLE Compra ADD COLUMN IF NOT EXISTS fecha_pago TIMESTAMPTZ",
        "ALTER TABLE DetalleCompra ADD COLUMN IF NOT EXISTS id_oferta INT REFERENCES Oferta(id)",
        "ALTER TABLE Pago ADD COLUMN IF NOT EXISTS clave_proveedor UUID UNIQUE",
        "ALTER TABLE Pago ADD COLUMN IF NOT EXISTS checkout_url TEXT",
        "ALTER TABLE Pago ADD COLUMN IF NOT EXISTS proveedor_app_id VARCHAR(120)",
        "ALTER TABLE Pago ADD COLUMN IF NOT EXISTS proveedor_user_id VARCHAR(120)",
        "CREATE TABLE IF NOT EXISTS ReservaCompra ("
        "id_compra INT NOT NULL REFERENCES Compra(id) ON DELETE CASCADE, "
        "id_producto INT NOT NULL, id_bodega INT NOT NULL, "
        "cantidad INT NOT NULL CHECK (cantidad > 0), "
        "estado VARCHAR(20) NOT NULL DEFAULT 'activa', "
        "PRIMARY KEY (id_compra, id_producto), "
        "FOREIGN KEY (id_producto, id_bodega) REFERENCES ProductosBodega(id_producto, id_bodega))",
        "CREATE INDEX IF NOT EXISTS ix_reserva_activa "
        "ON ReservaCompra (id_producto, id_bodega) WHERE estado = 'activa'",
    ]
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        for statement in statements:
            conn.execute(statement)
        for nombre in BASE_CATEGORIAS:
            ensure_category(conn, nombre)
        ensure_demo_admin(conn)
        # One-time migration: the original seed stored one password in plain
        # text. Rehash any such row so every stored password is a bcrypt hash.
        for table in ("Jefe", "Empleado", "Admin"):
            rows = conn.execute(f"SELECT id, password FROM {table}").fetchall()
            for row in rows:
                stored = row["password"]
                if not stored.startswith(("$2a$", "$2b$", "$2y$")):
                    conn.execute(
                        f"UPDATE {table} SET password = %s WHERE id = %s",
                        (hash_password(stored), row["id"]),
                    )
        # Keyed demo purchases: safe to call on every startup.
        ensure_demo_sales(conn)


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


def normalize_category(value):
    return " ".join(str(value or "").split())[:100]


def list_categories(conn) -> list:
    rows = conn.execute("SELECT nombre FROM Categoria ORDER BY nombre").fetchall()
    return [row["nombre"] for row in rows]


def ensure_category(conn, value) -> str:
    """Reuse an existing category or add it to the persistent catalog."""
    nombre = normalize_category(value)
    if not nombre:
        return ""
    conn.execute(
        "INSERT INTO Categoria (nombre) SELECT %s "
        "WHERE NOT EXISTS (SELECT 1 FROM Categoria WHERE lower(nombre) = lower(%s)) "
        "ON CONFLICT DO NOTHING",
        (nombre, nombre),
    )
    return conn.execute(
        "SELECT nombre FROM Categoria WHERE lower(nombre) = lower(%s)", (nombre,)
    ).fetchone()["nombre"]


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
        row = conn.execute(
            "SELECT id_bodega FROM Jefe WHERE id = %s AND COALESCE(estado, 'activo') = 'activo'",
            (who["id"],),
        ).fetchone()
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
    # One address cannot belong to two platform roles. This keeps /auth/signup,
    # /profiles/employees and /admin/users consistent with each other.
    for table in ("Jefe", "Empleado", "Admin", "Cliente"):
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
