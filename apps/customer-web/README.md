# customer-web

Tienda pública de BodeSmart. Comparte colores, tipografía y marca con `operations-web`.
El inicio muestra cada bodega y sus productos con precios, o solo las bodegas
en tarjetas. La búsqueda general agrupa resultados por bodega. El menú de
precio permite ordenar de menor a mayor, de mayor a menor o elegir un rango;
también se puede filtrar por días máximos hasta el vencimiento. Agregar un
producto abre la página de esa bodega. La
cesta sigue limitada a una sola bodega. También permite registrarse, comprar
y consultar pedidos. La reserva dura diez
minutos. El recojo en bodega es informativo.

## Desarrollo local

1. Inicia PostgreSQL y el backend con `DATABASE_URL` apuntando a la base local.
2. En esta carpeta ejecuta `npm ci` y `npm run dev`.
3. Abre `http://127.0.0.1:5174`. `npm run build` genera `dist/` y
   `npm test` comprueba búsqueda, filtros y agrupación.

La variable opcional `VITE_API_BASE_URL` cambia la API; su valor local es
`http://127.0.0.1:8000`. No coloques claves de Mercado Pago en Vite.

## API del comprador

| Ruta | Uso |
| --- | --- |
| `GET /customer/stores`, `GET /customer/offers` | Bodegas y ofertas públicas con disponibilidad descontando reservas |
| `POST /customer/auth/register`, `POST /customer/auth/login`, `GET /customer/auth/me` | Cuenta del comprador |
| `GET /customer/orders`, `GET /customer/orders/{id}` | Historial y detalle propios |
| `POST /customer/orders` | Pedido de una bodega, total congelado y reserva completa o ninguna |
| `POST /customer/orders/{id}/simulate-payment` | Pago local de demo; se puede desactivar con `ALLOW_SIMULATED_PAYMENT=false` |
| `POST /customer/orders/{id}/checkout`, `POST /customer/orders/{id}/verify-payment` | Mercado Pago de prueba y verificación por servidor |
| `POST /customer/payments/webhook` | Notificación firmada de Mercado Pago; requiere URL pública para uso remoto |

La integración externa requiere `MERCADOPAGO_ACCESS_TOKEN` de **prueba** en el
backend. Sin esa variable, la interfaz permite pago simulado local. Nunca se
descuenta inventario por la vuelta del navegador: solo por una aprobación
verificada o la simulación local. Un pago acreditado después de perder la
reserva queda en revisión, sin tomar existencias de otro pedido.

`seed_customer_demo.py` carga tres bodegas con precios de demostración distintos
para un mismo producto y crea cuentas locales. Exige
`BODESMART_DEMO_SEED=1` y escribe contraseñas aleatorias en
`.demo-credentials.json`, ignorado por Git. No ejecutes ese script en producción.

## Alcance de esta integración

La compra usa `ProductosBodega`, que en `main` guarda un saldo y vencimiento
por producto y bodega. La gestión de varios lotes de un mismo producto sigue
pendiente de integrar con la vista de operaciones; este frontend no muestra
un lote que el backend actual aún no distingue. Tampoco incorpora reparto,
devoluciones ni confirmación de recojo.
