# Logos oficiales

Esta carpeta recibe los logos oficiales copiados desde
`apps/operations-web/src/assets`:

- `BodeSmart-Logo.png` (marca completa)
- `BodeSmart-Mobile-Logo.png` (marca compacta)

La copia la hace `npm run copy-logos`, que npm ejecuta automáticamente antes de
`npm run dev` y `npm run build` mediante los hooks `predev` y `prebuild`. Si la
carpeta de `operations-web` no está disponible (por ejemplo, en una imagen
Docker cuyo contexto es solo `customer-web`), el script no falla y conserva los
archivos ya presentes aquí. `src/components/Brand.jsx` los sirve desde
`/assets/...`; en el panel de acceso el logo completo queda directo sobre el
verde, sin recuadro. No editar estos binarios a mano: se regeneran desde la
fuente oficial.
