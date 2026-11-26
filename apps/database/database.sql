
CREATE TABLE Bodega (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    direccion VARCHAR(255) NOT NULL
);

CREATE TABLE Jefe (
    id SERIAL PRIMARY KEY,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    correo VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    id_bodega INT UNIQUE NOT NULL,

    FOREIGN KEY (id_bodega) REFERENCES Bodega(id)
);

CREATE TABLE Empleado (
    id SERIAL PRIMARY KEY,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    correo VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    id_jefe INT NOT NULL,

    FOREIGN KEY (id_jefe) REFERENCES Jefe(id)
);

-- Category catalog. Categories grow over time; each product uses exactly one.
CREATE TABLE Categoria (
    nombre VARCHAR(100) PRIMARY KEY,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- The product is the catalog: it involves no inventory or warehouse storage.
-- categoria stores the single Categoria.nombre assigned to the product.
CREATE TABLE Producto (
    id SERIAL PRIMARY KEY,
    icono VARCHAR(100),
    nombre VARCHAR(100) NOT NULL,
    categoria VARCHAR(100),
    unidad_medida VARCHAR(50)
);

-- Inventory by warehouse: one row per product in each warehouse.
CREATE TABLE ProductosBodega (
    id_producto INT NOT NULL,
    id_bodega INT NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    precio_venta DECIMAL(10,2) NOT NULL,
    fecha_vencimiento DATE,
    estado VARCHAR(50) NOT NULL,

    PRIMARY KEY (id_producto, id_bodega),

    FOREIGN KEY (id_producto) REFERENCES Producto(id),
    FOREIGN KEY (id_bodega) REFERENCES Bodega(id)
);

CREATE TABLE Admin (
    id SERIAL PRIMARY KEY,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    correo VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'activo',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Cliente (
    id SERIAL PRIMARY KEY,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    correo VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    telefono VARCHAR(20),
    estado VARCHAR(20) NOT NULL DEFAULT 'activo',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Oferta (
    id SERIAL PRIMARY KEY,
    id_producto INT NOT NULL REFERENCES Producto(id),
    id_bodega INT REFERENCES Bodega(id),
    precio_original DECIMAL(10,2),
    precio_oferta DECIMAL(10,2) NOT NULL,
    fecha_inicio TIMESTAMP NOT NULL,
    fecha_fin TIMESTAMP NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'activo',
    es_generada BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE Carrito (
    id SERIAL PRIMARY KEY,
    id_cliente INT NOT NULL REFERENCES Cliente(id),
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE DetalleCarrito (
    id SERIAL PRIMARY KEY,
    id_carrito INT NOT NULL REFERENCES Carrito(id),
    id_producto INT NOT NULL REFERENCES Producto(id),
    cantidad INT NOT NULL CHECK (cantidad > 0),
    precio_unitario DECIMAL(10,2) NOT NULL
);

CREATE TABLE Compra (
    id SERIAL PRIMARY KEY,
    id_cliente INT NOT NULL REFERENCES Cliente(id),
    id_bodega INT NOT NULL REFERENCES Bodega(id),
    total DECIMAL(10,2) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    fecha_compra TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_recojo TIMESTAMP,
    reserva_hasta TIMESTAMPTZ,
    idempotency_key UUID UNIQUE,
    request_hash VARCHAR(64),
    fecha_pago TIMESTAMPTZ
);

CREATE TABLE DetalleCompra (
    id SERIAL PRIMARY KEY,
    id_compra INT NOT NULL REFERENCES Compra(id),
    id_producto INT NOT NULL REFERENCES Producto(id),
    id_oferta INT REFERENCES Oferta(id),
    cantidad INT NOT NULL CHECK (cantidad > 0),
    precio_unitario DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL
);

CREATE TABLE Pago (
    id SERIAL PRIMARY KEY,
    id_compra INT NOT NULL REFERENCES Compra(id),
    metodo_pago VARCHAR(50) NOT NULL,
    id_transaccion_externa VARCHAR(150),
    monto DECIMAL(10,2) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    fecha_pago TIMESTAMP,
    clave_proveedor UUID UNIQUE,
    checkout_url TEXT,
    proveedor_app_id VARCHAR(120),
    proveedor_user_id VARCHAR(120)
);

CREATE TABLE ReservaCompra (
    id_compra INT NOT NULL REFERENCES Compra(id) ON DELETE CASCADE,
    id_producto INT NOT NULL,
    id_bodega INT NOT NULL,
    cantidad INT NOT NULL CHECK (cantidad > 0),
    estado VARCHAR(20) NOT NULL DEFAULT 'activa',
    PRIMARY KEY (id_compra, id_producto),
    FOREIGN KEY (id_producto, id_bodega) REFERENCES ProductosBodega(id_producto, id_bodega)
);

CREATE INDEX ix_reserva_activa ON ReservaCompra (id_producto, id_bodega) WHERE estado = 'activa';