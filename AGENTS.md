# Instrucciones para agentes de IA

Antes de trabajar, lee esta guía y los documentos relevantes de `docs/`.

## Reglas
- No inventes requisitos, resultados de entrevistas, tecnologías ni decisiones.
- Distingue confirmado, derivado, propuesto y pendiente.
- Conserva identificadores CU-01…CU-09, EN-01…EN-08, RN-01…RN-09, AN-01…AN-03 y TN-01…TN-03.
- Mantén trazabilidad entre casos, requisitos, reglas, entidades, pruebas y código.
- El jefe puede realizar operaciones del empleado; el empleado accede únicamente a su bodega.
- Cada movimiento debe identificar responsable, productos, lotes y cantidades positivas.
- Una salida no puede superar stock disponible y descuenta stock una sola vez.
- No se venden productos vencidos o registrados como deteriorados.
- Solo el jefe modifica precios y aprueba promociones/sugerencias.
- La IA apoya decisiones. Nunca aprueba por sí sola, genera compras ni modifica inventario por una sugerencia.
- No amplíes el MVP con proveedores, pagos, facturación electrónica, delivery, contabilidad, voz/fotografía o estimación de vida útil por IA sin cambio de alcance aprobado.
- No afirmes que el producto está implementado ni que reduce pérdidas: las entrevistas son exploratorias.

## SDD por funcionalidad
Discover → Specify → Review → Plan → Tasks → Implement → Validate → Learn.
Trabaja incrementalmente. No exijas especificar todo el sistema antes de iniciar. Si detectas contradicciones, regístralas como preguntas abiertas o ADR; no las resuelvas en silencio.
