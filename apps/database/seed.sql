-- BodeSmart seed data for operations-web.
-- Run after database.sql (PostgreSQL 17).
--
-- Derived assumptions, not confirmed:
-- - Warehouse address is empty because it was not provided.
-- - ProductosBodega.estado = 'activo', derived from activo: true in demoData.js.
--
-- No manager credentials are stored here. The account is created through
-- /auth/signup, which hashes the password with bcrypt before storing it.
-- The only exception is the demo platform admin below: its readable password
-- is rehashed by ensure_schema() on the first backend startup. It is a local
-- prototype credential, not a real account.
--
-- Demo purchases are not inserted here: the backend seeds them once through
-- ensure_demo_sales() after ensure_schema(), so an existing database also gets
-- the same synthetic purchases without decrementing stock twice.

BEGIN;

INSERT INTO Bodega (id, nombre, direccion)
VALUES (1, 'Bodega San Martín', '')
ON CONFLICT DO NOTHING;

-- Demo platform administrator for admin-web. bcrypt hashing happens at startup.
INSERT INTO Admin (id, nombres, apellidos, correo, password, estado)
VALUES (1, 'Admin', 'Plataforma', 'admin@bodesmart.local', 'Admin123456', 'activo')
ON CONFLICT DO NOTHING;

-- Initial category catalog. New categories are added from the register form.
INSERT INTO Categoria (nombre) VALUES
('Abarrotes'), ('Lácteos'), ('Frutas'), ('Bebidas'), ('Limpieza'),
('Snacks'), ('Conservas'), ('Cuidado personal'), ('Otros')
ON CONFLICT DO NOTHING;

-- Catalog: products without stock or warehouse assignment.
INSERT INTO Producto (id, icono, nombre, categoria, unidad_medida) VALUES
(1,  '🥛', 'Leche Gloria entera',  'Lácteos',          'unid.'),
(2,  '🥛', 'Yogurt natural',       'Lácteos',          'unid.'),
(3,  '🍌', 'Plátano de seda',      'Frutas',           'kg'),
(4,  '🍚', 'Arroz extra',          'Abarrotes',        'unid.'),
(5,  '🥤', 'Gaseosa familiar',     'Bebidas',          'unid.'),
(6,  '🧼', 'Detergente en polvo',  'Limpieza',         'unid.'),
(7,  '🍪', 'Galletas de soda',     'Snacks',           'unid.'),
(8,  '🥫', 'Atún en lata',         'Conservas',        'unid.'),
(9,  '🧼', 'Jabón de tocador',     'Cuidado personal', 'unid.'),
(10, '🥤', 'Agua mineral',         'Bebidas',          'unid.'),
(11, '🥛', 'Leche chocolatada',    'Lácteos',          'unid.'),
(12, '🥛', 'Yogurt de fresa',      'Lácteos',          'unid.'),
(13, '🍎', 'Manzana roja',         'Frutas',           'kg'),
(14, '🍜', 'Fideos largos',        'Abarrotes',        'unid.'),
(15, '🧼', 'Lejía',                'Limpieza',         'unid.'),
(16, '🍟', 'Papas fritas',         'Snacks',           'unid.'),
(17, '🥫', 'Sardinas en lata',     'Conservas',        'unid.'),
(18, '🧴', 'Shampoo familiar',     'Cuidado personal', 'unid.'),
(19, '🧃', 'Jugo de naranja',      'Bebidas',          'unid.'),
(20, '🍚', 'Avena en hojuelas',    'Abarrotes',        'unid.'),
(21, '🧀', 'Queso fresco',         'Lácteos',          'unid.'),
(22, '🍅', 'Tomate italiano',      'Frutas',           'kg'),
(23, '🍞', 'Pan de molde',         'Abarrotes',        'unid.'),
(24, '🧃', 'Jugo de mango',        'Bebidas',          'unid.'),
(25, '🍖', 'Jamón cocido',         'Conservas',        'unid.'),
(26, '🧴', 'Crema corporal',       'Cuidado personal', 'unid.')
ON CONFLICT DO NOTHING;

-- Inventory for Bodega San Martín.
INSERT INTO ProductosBodega (
    id_producto, id_bodega, stock, precio_venta, fecha_vencimiento, estado
) VALUES
(1,  1,  8,  4.50, DATE '2026-10-20', 'activo'),
(2,  1,  5,  3.80, DATE '2026-10-21', 'activo'),
(3,  1, 12,  3.50, DATE '2026-10-22', 'activo'),
(4,  1, 24,  4.20, DATE '2027-06-10', 'activo'),
(5,  1, 10,  7.50, NULL,              'activo'),
(6,  1,  6,  8.90, NULL,              'activo'),
(7,  1, 15,  2.50, DATE '2027-01-15', 'activo'),
(8,  1,  9,  6.40, DATE '2028-03-20', 'activo'),
(9,  1,  7,  3.20, NULL,              'activo'),
(10, 1, 18,  2.50, NULL,              'activo'),
(11, 1,  8,  4.80, DATE '2027-02-10', 'activo'),
(12, 1,  6,  4.20, DATE '2027-01-28', 'activo'),
(13, 1, 14,  4.50, DATE '2026-12-10', 'activo'),
(14, 1, 20,  3.20, DATE '2028-01-12', 'activo'),
(15, 1,  5,  4.90, NULL,              'activo'),
(16, 1, 11,  3.50, DATE '2027-04-18', 'activo'),
(17, 1,  7,  5.80, DATE '2028-04-20', 'activo'),
(18, 1,  4, 12.50, NULL,              'activo'),
(19, 1,  9,  5.50, DATE '2027-03-12', 'activo'),
(20, 1, 13,  4.10, DATE '2028-02-08', 'activo'),
(21, 1,  4,  8.50, DATE '2026-11-20', 'activo'),
(22, 1,  6,  4.20, DATE '2026-11-21', 'activo'),
(23, 1,  5,  6.90, DATE '2026-11-22', 'activo'),
(24, 1,  8,  5.90, DATE '2026-11-23', 'activo'),
(25, 1,  3,  9.80, DATE '2026-11-24', 'activo'),
(26, 1,  4, 11.50, DATE '2026-11-25', 'activo')
ON CONFLICT DO NOTHING;

-- Reset SERIAL sequences after inserting explicit IDs.
SELECT setval(pg_get_serial_sequence('Bodega', 'id'), COALESCE((SELECT MAX(id) FROM Bodega), 1));
SELECT setval(pg_get_serial_sequence('Admin', 'id'), COALESCE((SELECT MAX(id) FROM Admin), 1));
SELECT setval(pg_get_serial_sequence('Jefe', 'id'), COALESCE((SELECT MAX(id) FROM Jefe), 1));
SELECT setval(pg_get_serial_sequence('Producto', 'id'), COALESCE((SELECT MAX(id) FROM Producto), 1));

COMMIT;
