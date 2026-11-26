# Tareas — REC-IA

| Tarea | Estado | Resultado verificable / criterio de finalización |
|---|---|---|
| Revisar y aprobar la especificación | Pendiente | Revisión del equipo; se confirma proveedor y alcance, pero no se cierra el modelo. |
| Resolver preguntas bloqueantes | Pendiente | Modelo y cuota real; decisión sobre persistencia de EN-08. |
| Registrar la decisión del proveedor | Hecho | `ADR-004`; proveedor Gemini, clave solo en backend. |
| Definir el contrato HTTP y el esquema de salida | Hecho | `POST /recommendations/generate` documentado en `plan.md` y `spec.md`. |
| Implementar el adaptador de Gemini | Hecho | `apps/backend/ai.py` con campos permitidos, esquema, saneamiento y `store: false`. |
| Implementar el endpoint jefe-only | Hecho | Router registrado; verificación de rol y bodega antes de la llamada externa. |
| Implementar la pantalla y la navegación | Hecho | Sección `jefeOnly` y revisión de precio vía `PATCH /products/{id}`. |
| Documentar despliegue y variables | Hecho | `.env.example` y `docker-compose.yml` con `GEMINI_API_KEY` / `GEMINI_MODEL`. |
| Añadir pruebas automatizadas | Hecho | `tests/test_ai_recommendations.py` y nuevos casos en `tests/test_backend_api.py`. |
| Ejecutar pruebas y compilación | Pendiente | `pytest` y `npm run build` ejecutados; resultados registrados en `docs/06-quality/README.md`. |
| Configurar la clave real del usuario | Pendiente | `.env` local y EC2 con `GEMINI_API_KEY` real; nunca versionado. |
| Validar una respuesta real de Gemini | Pendiente | Respuesta saneada, justificación comprensible y ausencia de mutación comprobada. |
| Confirmar generación real en local | Hecho | El usuario confirmó tarjetas generadas con `GEMINI_API_KEY` real y `gemini-3.1-flash-lite`; queda pendiente la corrida automatizada. |
| Conservar recomendaciones en la UI y mostrar icono | Hecho | Estado en `App.jsx`, botón `button-soft` “Volver a generar recomendaciones” e icono del producto a la izquierda del nombre. |
| Actualizar trazabilidad y calidad con el resultado | Pendiente | `traceability.md`, `open-questions.md` y `docs/06-quality/README.md` alineados. |

Las tareas marcadas como hechas describen código escrito en el prototipo; no implican que la integración haya sido validada contra el proveedor real.
