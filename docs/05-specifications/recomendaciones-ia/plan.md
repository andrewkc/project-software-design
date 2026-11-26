# Plan técnico — REC-IA

**Estado:** Aprobado para el prototipo por decisión del usuario sobre proveedor y alcance. El modelo concreto y la cuota real siguen pendientes.

## Enfoque propuesto

Un adaptador delgado en el backend llama a la API de Gemini y devuelve sugerencias saneadas. El frontend solo consume el endpoint y abre el formulario de edición existente cuando el jefe decide revisar un precio. No se agrega una tabla de sugerencias ni lógica de compras.

## Componentes afectados

| Capa | Archivo | Cambio |
|---|---|---|
| Configuración | `apps/backend/config.py` | Lee `GEMINI_API_KEY`, `GEMINI_MODEL` y `GEMINI_API_URL`. |
| Adaptador IA | `apps/backend/ai.py` | Prompt con campos permitidos, salida JSON estructurada, saneamiento y errores controlados. |
| API | `apps/backend/routers/recommendations.py` | `POST /recommendations/generate`, jefe-only y filtrado por bodega. |
| Arranque | `apps/backend/main.py` | Registro del router. |
| Cliente HTTP | `apps/operations-web/src/lib/api.js` | Helper `generateRecommendations()`. |
| UI | `apps/operations-web/src/features/recommendations/RecommendationsPage.jsx` | Pantalla jefe-only con generación, tarjetas y revisión de precio. |
| Navegación | `apps/operations-web/src/App.jsx`, `src/data/demoData.js` | Ruta `recommendations` con `jefeOnly: true`. |
| Estilos | `apps/operations-web/src/styles.css` | Tarjetas, aviso y modal de revisión. |
| Despliegue | `docker-compose.yml`, `.env.example` | Variables inyectadas solo al backend. |

## Contratos / interfaces

### `POST /recommendations/generate`

- Autenticación: `Authorization: Bearer <token>`.
- Respuesta `200`:

```json
{
  "generadas_en": "2026-11-25T12:00:00+00:00",
  "modelo": "gemini-3.1-flash-lite",
  "recomendaciones": [
    {
      "id_producto": 1,
      "nombre": "Yogurt natural",
      "tipo": "descuento",
      "justificacion": "Vence pronto y hay 2 unidades.",
      "precio_actual": 8.0,
      "precio_sugerido": 6.5
    },
    {
      "id_producto": 2,
      "nombre": "Arroz extra",
      "tipo": "reposicion",
      "justificacion": "Stock actual 20 unidades.",
      "stock_actual": 20,
      "cantidad_sugerida": 3
    }
  ],
  "aviso": "Sugerencias informativas, no validadas. La IA no aprueba cambios, no genera compras ni modifica inventario: el jefe decide."
}
```

- Respuesta `401`: sin token o token inválido.
- Respuesta `403`: rol distinto de jefe.
- Respuesta `503`: IA no configurada o proveedor no disponible.

### Llamada a Gemini

Se usa `POST https://generativelanguage.googleapis.com/v1beta/interactions` con cabecera `x-goog-api-key`. Se cambió desde `v1` para compartir endpoint con REG-IA, que necesita `v1beta` para multimedia inline. El cuerpo incluye `model`, `input`, `system_instruction`, `response_format` con esquema JSON y `store: false`. La salida se acepta desde `output_text`, desde `steps[].content[].text` o desde un objeto con `recomendaciones`.

## Datos y persistencia

No hay escrituras en PostgreSQL durante la generación. La sugerencia se construye en memoria y se devuelve al navegador. `store: false` evita que el proveedor retenga el prompt derivado del inventario. El único cambio persistente ocurre si el jefe confirma manualmente el precio con `PATCH /products/{id}`.

## Seguridad y permisos

- La clave vive en `.env` (ignorado) y se inyecta solo en el contenedor `backend`.
- El frontend no recibe la clave: las pruebas estáticas lo comprueban.
- Verificación de rol antes de consultar el proveedor y filtro por `bodega_id_for`.
- Los campos del prompt están permitidos explícitamente; no se envían correos, nombres de empleado ni datos de otras bodegas.
- El esquema de salida y el saneamiento impiden tipos arbitrarios, ids ajenos y valores no positivos.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| El modelo inventa costos, márgenes o ventas | System instruction y Prompt con campos cerrados; justificación libre pero etiquetada como no validada. |
| El modelo devuelve JSON inválido | `503` controlado; nunca se muestra como válido. |
| Sugerencia contradictoria con RN-09 | Saneamiento: descuento menor y aumento mayor que el precio actual. |
| Cuota agotada en tier gratuito | Error visible; inventario, alertas y consultas siguen disponibles. |
| Fuga de clave al cliente | Variable solo en backend y prueba estática sobre `src/`. |
| Retención de datos por el proveedor | `store: false`. |

## Decisiones requeridas

- **Confirmada:** proveedor Gemini y alcance con descuentos, aumentos, precios y reposición.
- **Pendiente:** modelo definitivo y cuota disponible en la cuenta del usuario.
- **Pendiente:** persistencia futura de EN-08 y promociones con vigencia.

## Validación técnica

- Paridad estática entre rutas del backend y llamadas de `api.js`.
- Pruebas unitarias del adaptador sin red.
- Pruebas HTTP con backend y base en marcha: `403` para empleado, `503` sin clave y no mutación de productos.
- Compilación del frontend con `npm run build`.
- Validación real con `GEMINI_API_KEY`: **pendiente** hasta que el usuario proporcione la clave.
