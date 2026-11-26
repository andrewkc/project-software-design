# ADR-009: Shell móvil de hamburguesa y favicon compartido

**Estado:** Solicitado por el producto el 2026-11-26. Implementado como propuesta en `operations-web`, `customer-web` y `admin-web`. Pendiente de `npm run build`, reconstrucción con Docker y revisión visual en navegador/dispositivo.

**Fecha:** 2026-11-26

## Contexto

Las tres aplicaciones web ya compartían paleta, tipografía (`--font-scale: 1.4`) y logos. `operations-web` sirve el favicon desde `public/favicon.png`, pero `customer-web` y `admin-web` no lo referenciaban en `index.html`.

En móvil (≤720 px) cada app mostraba una barra inferior fija con todas las secciones: cuatro en `customer-web`, tres en `admin-web` y cinco en `operations-web` (más `Perfil` para el empleado). La barra ocupaba el ancho completo, reducía el espacio de contenido y obligaba a usar textos de `7px × escala` (~9,8 px) para que cupieran todas las etiquetas. El usuario pidió específicamente un menú desplegable de hamburguesa en la parte inferior, no una barra con muchas secciones, y una tipografía normal/proporcional y legible.

La solicitud no proviene de una entrevista: es una decisión de producto para el prototipo y se registra como tal. No amplía el MVP con funcionalidad nueva ni afirma usabilidad validada.

## Decisión

1. Las tres apps sirven el mismo archivo `public/favicon.png` mediante `<link rel="icon" type="image/png" href="/favicon.png" />` en `index.html`. No se genera ni se versiona ningún asset nuevo.
2. Bajo `@media (max-width: 720px)`, se retira la barra inferior fija. En su lugar, un botón de hamburguesa en la esquina inferior derecha (`aria-haspopup="menu"`, `aria-expanded`, `aria-controls`) abre un panel hacia arriba (`role="menu"`) con **todas** las secciones disponibles para el rol. Al elegir una sección, el panel se cierra y se navega; el botón usa `Icon name={open ? "close" : "menu"}`.
3. El panel respeta las reglas existentes: en `operations-web` el jefe ve `Recomendaciones` y `Empleados`, el empleado ve `Perfil`; en `customer-web` y `admin-web` no se agrega una entrada con la etiqueta `Perfil`, sino «Mi cuenta», porque la tarjeta de cuenta ya abría el perfil en escritorio y en móvil el sidebar está oculto.
4. La escala móvil general pasa de `1.4` a `1.55` mediante `body { --font-scale: 1.55; }`. La pantalla de acceso mantiene `1.4` para no requerir desplazamiento. Las etiquetas secundarias, celdas de tabla, badges y textos de `7px`/`8px` tienen un piso de `calc(9px * var(--font-scale))` (~14 px). No se usa `zoom`, para no deformar controles ni alterar el viewport.
5. El margin inferior de `.main-area` se ajusta para que el botón flotante no tape contenido; las notificaciones y filtros flotantes se desplazan por encima del botón.

## Alternativas consideradas

- **Mantener la barra inferior pero con menos secciones:** se descartó porque el usuario pidió ver *todas* las secciones sin una barra fija cargada.
- **Usar `zoom` o reducir fuentes globalmente:** se descartó porque empeora la legibilidad y contradice la solicitud.
- **Un drawer lateral en móvil:** se descartó por coherencia con el patrón ya usado en escritorio (sidebar) y porque el usuario pidió el disparador en la parte inferior.

## Consecuencias

- Cambian tres componentes de layout y tres hojas de estilo; los contratos de API, roles, precios, stock y pagos no se tocan.
- Las pruebas estáticas existentes que buscaban `grid-template-columns` en `.mobile-nav` quedan obsoletas; se sustituyen por comprobaciones del panel desplegable y de accesibilidad básica en `tests/test_web_shell_contract.py`.
- La fuente `1.55` puede hacer que alguna tabla ancha requiera scroll horizontal en pantallas muy estrechas; se mantiene `overflow-x: auto` donde ya existía y queda pendiente la revisión visual.
- No se afirma que el diseño reduzca pérdidas ni que esté validado con usuarios reales.

## Trazabilidad

- Solicitud del producto registrada en [scope.md](../../01-product/scope.md) y [non-functional-requirements.md](../../03-requirements/non-functional-requirements.md).
- Implementación: `AdminLayout.jsx`, `CustomerLayout.jsx`, `OperationsLayout.jsx`, los tres `styles.css` y los tres `index.html`.
- Validación estática: `tests/test_web_shell_contract.py`; cobertura general en [docs/06-quality](../06-quality/README.md).
- No crea nuevos RF, RN ni EN: es una decisión de interfaz, no de regla de negocio.
