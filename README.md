# SDD Documentation Starter — Gestión interna de bodegas

Versión inicial estructurada a partir del README autocontenido **Entregable 1 — Modelado del negocio**. Incluye el modelo de negocio, las tres respuestas de entrevistas, nueve casos de uso, ocho entidades, nueve reglas, trazabilidad y diagramas Mermaid.

**Importante:** esta documentación describe una propuesta de MVP; no acredita que el software esté implementado. La arquitectura técnica, stack, base de datos, despliegue, proveedor/modelo de IA y métricas no funcionales siguen pendientes.

## Estructura
- `AGENTS.md`: instrucciones comunes para asistentes de IA.
- `.agents/skills/sdd-documentation-architect/`: procedimiento SDD reutilizable.
- `docs/00-governance/`: constitución, flujo, glosario e inventario.
- `docs/01-product/`: visión, alcance y roadmap.
- `docs/02-business/`: organización, entrevistas, actores, trabajadores, casos, entidades, reglas, diagramas y trazabilidad.
- `docs/03-requirements/`: requisitos funcionales iniciales, NFR pendientes y preguntas abiertas.
- `docs/04-architecture/`: modelo de dominio y diagramas.
- `docs/05-specifications/`: plantillas de spec, plan y tasks.
- `docs/06-quality/`: áreas de validación.
- `docs/07-evidence/`: entrevistas en Markdown/CSV y README fuente.
- `templates/`: plantillas ADR y requisitos.

## Inicio recomendado
1. Leer `AGENTS.md` y `docs/00-governance/constitution.md`.
2. Revisar visión, alcance y modelo de negocio.
3. Resolver preguntas abiertas antes de fijar decisiones técnicas.
4. Para cada funcionalidad, crear una especificación desde `docs/05-specifications/_feature-template/`.
5. Mantener trazabilidad entre spec, requisitos, reglas, entidades, pruebas e implementación.

## Etiquetas de certeza
- **Confirmado:** explícito en la fuente.
- **Derivado:** consecuencia directa de información confirmada.
- **Propuesto:** recomendación aún no aprobada.
- **Pendiente:** la fuente no lo define.
