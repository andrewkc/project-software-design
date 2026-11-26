# Contexto del sistema

Aplicación interna para administrador de app, jefe y empleado, más `customer-web` como vista pública para compradores (ADR-007). No hay proveedor logístico como actor. El comprador usa la misma API y la misma base; la aprobación del pago siempre la decide el backend.

## Integración externa de apoyo (ADR-004)

Para el prototipo se usa Gemini como proveedor de recomendaciones bajo demanda y de borradores de registro asistido con `Foto`/`Voz` (ADR-005). El backend es el único que conoce la clave. En recomendaciones envía solo campos ya existentes del inventario de la bodega (`nombre`, `categoria`, `stock`, `precio_venta`, `fecha_vencimiento`, `estado`). En registro asistido recibe multimedia del navegador (foto o voz), valida MIME/tamaño y envía el archivo en línea con `store: false`. `Voz` transcribe los ocho campos dictados, incluidos precio, vencimiento y código cuando se dicen explícitamente; no estima vida útil. El modo `Código` valida la imagen, toma los dígitos procesados en el navegador y consulta la API pública de Open Food Facts; su botón del medio alterna entre capturar la imagen enfocada y encender la cámara. El proveedor no toma decisiones ni escribe datos.

La categoría del producto se persiste en un catálogo `Categoria` con nueve valores base, creado y ampliado desde endpoints autenticados `GET /categories` y `POST /categories`; cada producto guarda un solo nombre de categoría como detalle de EN-03, con reutilización insensible a mayúsculas/minúsculas (RN-14/RF-29). El selector de Ícono usa 124 emojis con keywords y mantiene paridad exacta entre frontend y backend (RF-30). El modelo es configurable y el default provisional es `gemini-3.1-flash-lite`, elegido después de que `gemini-3.5-flash-lite` devolviera `503` por alta demanda en la prueba local; `Foto`/`Voz` pueden elegir entre los ids autorizados por `GET /ai/models`, con validación en el backend y clave solo en el servidor (RF-34/RN-17). No se usa `google_search` porque *Search grounding* no está disponible en el plan gratuito.

El flujo es: navegador del jefe → API de BodeSmart → Interactions API de Gemini → respuesta saneada en memoria → revisión manual del jefe → `PATCH /products/{id}` solo si el jefe confirma. La recomendación de reposición no genera compras ni movimientos.

## Integración de pago de prueba (ADR-007)

`customer-web` consume `/customer/stores`, `/customer/offers`, `/customer/auth/*` y `/customer/orders`. En el pago de prueba, el navegador abre Mercado Pago en modo prueba o llama a la simulación local; el backend consulta al proveedor, valida importe, referencia, moneda y cuenta, y firma el webhook HMAC antes de aprobar. El único descuento de stock pasa por `sales_service.approve_reserved_order()`, compartido con `POST /sales`. No hay cobro real ni datos de tarjeta en el frontend.

Pendiente: clientes/dispositivos, persistencia de decisiones (EN-08), conectividad, cuota real del proveedor de IA, precisión real del dictado de voz, dominio y credenciales de Mercado Pago de prueba para el entorno compartido, ejecución de `pytest`/`npm run build`, operación y monitoreo.
