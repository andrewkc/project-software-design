import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id            TEXT PRIMARY KEY,
    role          TEXT NOT NULL CHECK (role IN ('jefe', 'empleado')),
    name          TEXT NOT NULL,
    nombres       TEXT NOT NULL DEFAULT '',
    apellidos     TEXT NOT NULL DEFAULT '',
    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    store         TEXT NOT NULL,
    activo        INTEGER NOT NULL DEFAULT 1,
    creado_en     TEXT NOT NULL,
    revocado_en   TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    token        TEXT PRIMARY KEY,
    profile_id   TEXT NOT NULL REFERENCES profiles(id),
    creado_en    TEXT NOT NULL,
    revocado_en  TEXT
);

CREATE TABLE IF NOT EXISTS products (
    id             TEXT PRIMARY KEY,
    store          TEXT NOT NULL,
    name           TEXT NOT NULL,
    category       TEXT NOT NULL,
    icon           TEXT NOT NULL DEFAULT '📦',
    stock          REAL NOT NULL DEFAULT 0,
    unit           TEXT NOT NULL DEFAULT 'unid.',
    price          REAL NOT NULL DEFAULT 0,
    expires        TEXT,
    creado_por     TEXT NOT NULL REFERENCES profiles(id),
    bloqueado      INTEGER NOT NULL DEFAULT 0,
    bloqueado_por  TEXT,
    activo         INTEGER NOT NULL DEFAULT 1,
    creado_en      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lots (
    id                   TEXT PRIMARY KEY,
    product_id           TEXT NOT NULL REFERENCES products(id),
    store                TEXT NOT NULL,
    codigo               TEXT NOT NULL,
    fecha_ingreso        TEXT NOT NULL,
    fecha_vencimiento    TEXT,
    cantidad_disponible  REAL NOT NULL DEFAULT 0,
    costo_unitario       REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS movements (
    id                 TEXT PRIMARY KEY,
    store              TEXT NOT NULL,
    fecha_hora         TEXT NOT NULL,
    tipo               TEXT NOT NULL CHECK (tipo IN ('entrada', 'salida', 'ajuste')),
    motivo             TEXT NOT NULL,
    total              REAL,
    responsable_id     TEXT NOT NULL REFERENCES profiles(id),
    responsable_nombre TEXT NOT NULL,
    producto_id        TEXT REFERENCES products(id),
    stock_anterior     REAL,
    stock_nuevo        REAL,
    diferencia         REAL
);

CREATE TABLE IF NOT EXISTS movement_details (
    id               TEXT PRIMARY KEY,
    movimiento_id    TEXT NOT NULL REFERENCES movements(id),
    producto_id      TEXT NOT NULL REFERENCES products(id),
    lote_id          TEXT REFERENCES lots(id),
    cantidad         REAL NOT NULL,
    importe_unitario REAL,
    subtotal         REAL
);

CREATE INDEX IF NOT EXISTS idx_products_store ON products(store);
CREATE INDEX IF NOT EXISTS idx_lots_product ON lots(product_id);
CREATE INDEX IF NOT EXISTS idx_movements_store ON movements(store);
"""


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with connect() as connection:
        connection.executescript(SCHEMA)


@contextmanager
def get_connection():
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()
