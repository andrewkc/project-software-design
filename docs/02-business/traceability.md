# Matriz de trazabilidad

| Caso | Actor | Trabajador | Entidades | Reglas |
|---|---|---|---|---|
| CU-01 | AN-01 | TN-01 | EN-01 | RN-01 |
| CU-02 | AN-02 | TN-02 | EN-01, EN-02, EN-03 | RN-02, RN-07, RN-12, RN-13, RN-14 |
| CU-03 | AN-02; AN-03 asignado | TN-02 | EN-01, EN-02 | RN-02 |
| CU-04 | AN-02, AN-03 | TN-03 o TN-02 | EN-01…EN-06 | RN-02, RN-03 |
| CU-05 | AN-02, AN-03 | TN-03 o TN-02 | EN-01…EN-07 | RN-02, RN-03, RN-04, RN-05, RN-06, RN-09 |
| CU-06 | AN-02, AN-03 | TN-03 o TN-02 | EN-01…EN-04 | RN-02, RN-04, RN-06 |
| CU-07 | AN-02 | TN-02 | EN-01…EN-06 | RN-02, RN-03 |
| CU-08 | AN-02 | TN-02 | EN-01…EN-04, EN-07, EN-08 | RN-02, RN-06, RN-07, RN-08, RN-09 |
| CU-09 | AN-02 | TN-02 | EN-01…EN-06, EN-08 | RN-02, RN-08 |
| REC-IA (amplía CU-08 y CU-09) | AN-02; Gemini como apoyo | TN-02 | EN-03, EN-04, EN-07, EN-08 | RN-02, RN-07, RN-08, RN-09 |
| REG-IA (amplía CU-02 y apoya CU-04) | AN-02, AN-03; Gemini como apoyo | TN-02, TN-03 | EN-03, EN-04, EN-08 | RN-02, RN-03, RN-08, RN-12, RN-13, RN-14, RN-17 |
| VENTAS-01 (amplía CU-05 y CU-07) | AN-02, AN-03; comprador como origen de los datos | TN-02, TN-03 | EN-01, EN-02, EN-03, EN-05, EN-06 | RN-02, RN-03, RN-04, RN-05, RN-06, RN-15, RN-16 |

## Trazabilidad de implementación de REC-IA y REG-IA

| Caso | Requisitos | Reglas | Decisión | Código | Pruebas |
|---|---|---|---|---|---|
| CU-08, CU-09 | RF-12, RF-13, RF-14, RF-24 | RN-02, RN-07, RN-08, RN-09 | ADR-004 | `apps/backend/ai.py`; `apps/backend/routers/recommendations.py`; `apps/operations-web/src/features/recommendations/RecommendationsPage.jsx` | `tests/test_ai_recommendations.py`; `tests/test_endpoint_usage.py`; `tests/test_backend_api.py` |
| CU-02, CU-04 | RF-25, RF-26, RF-27, RF-28, RF-29, RF-30, RF-34 | RN-02, RN-03, RN-08, RN-12, RN-13, RN-14, RN-17 | ADR-005 | `apps/backend/config.py`; `apps/backend/registration_ai.py`; `apps/backend/routers/registration.py`; `apps/backend/routers/categories.py`; `apps/backend/database.py`; `apps/backend/routers/products.py`; `apps/database/database.sql`; `apps/database/seed.sql`; `docker-compose.yml`; `apps/operations-web/src/features/products/AiModelPicker.jsx`; `useProductDraft.js`; `RegisterPage.jsx`; `ProductModal.jsx`; `App.jsx` | `tests/test_registration_ai.py`; `tests/test_endpoint_usage.py`; `tests/test_backend_api.py` |

RF-12 incluye ahora aumentos de precio por expansión de alcance confirmada. RF-13 y RF-14 permanecen como requisitos de reposición y visualización; las sugerencias no se persisten en EN-08 dentro de este corte. REG-IA tampoco persiste borradores: el usuario revisa y guarda mediante `POST /products`.

RF-29 y RN-14 cubren el catálogo persistente de categorías implementado como detalle de EN-03 (una categoría por producto, creable desde el registro y reutilizable sin distinguir mayúsculas/minúsculas); no agregan una entidad de negocio. RF-30 cubre el selector de ícono amplio con paridad frontend/backend y el botón alterno de cámara en `Código`. RF-34/RN-17 cubren el selector de modelo autorizado: la UI solo muestra ids publicados por `GET /ai/models`, `POST /products/extract` valida la allowlist y la clave permanece en el backend; no garantiza disponibilidad ante un `503`. La creación explícita de categoría persiste solo `Categoria`; la extracción y la IA no escriben productos, movimientos ni stock. **Estado:** implementado en prototipo; pendiente de `pytest`, `npm run build` y validación real del dictado.

## Trazabilidad de implementación de VENTAS-01

| Caso | Requisitos | Reglas | Decisión | Código | Pruebas |
|---|---|---|---|---|---|
| CU-05, CU-07 | RF-31, RF-32, RF-33 | RN-02, RN-03, RN-04, RN-05, RN-06, RN-15, RN-16 | ADR-006 | `apps/database/database.sql`; `apps/backend/database.py`; `apps/backend/sales_service.py`; `apps/backend/routers/sales.py`; `apps/backend/main.py`; `apps/operations-web/src/features/sales/SalesPage.jsx`; `App.jsx`; `api.js`; `demoData.js` | `tests/test_sales.py`; `tests/test_backend_api.py`; `tests/test_endpoint_usage.py` |

El historial expone solo `Compra.estado = 'pagado'`. `POST /sales` es el contrato transaccional que `customer-web` invoca a través del servicio compartido de descuento; en `operations-web` lo usa el jefe/empleado y la siembra demo con datos sintéticos. No se crean tablas `Movimiento`/`DetalleMovimiento` ni se asigna responsable de movimiento: esa parte del CU-05 sigue pendiente y registrada en preguntas abiertas.

## Trazabilidad de implementación de CLIENTE-01

| Caso | Requisitos | Reglas | Decisión | Código | Pruebas |
|---|---|---|---|---|---|
| CU-05, CU-07 | RF-31, RF-32, RF-33 | RN-02, RN-04, RN-05, RN-06, RN-15, RN-16 | ADR-007 | `apps/customer-web/src/**`; `apps/backend/routers/customer.py`; `apps/backend/sales_service.py`; `apps/backend/config.py`; `apps/backend/main.py`; `apps/backend/seed_customer_demo.py` | `tests/test_customer_contract.py`; `tests/test_customer_flow.py`; `tests/test_endpoint_usage.py` |

El comprador ve todos sus estados, mientras `Ventas` sigue filtrando solo `pagado`. El pago de prueba nunca es decidido por el navegador y el descuento de stock pasa por la misma función que `POST /sales`.
