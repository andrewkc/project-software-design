Los logos oficiales viven en `operations-web/src/assets` y se copian a
`customer-web/public/assets` con `npm run copy-logos` (ejecutado automáticamente
por `predev` y `prebuild`). Se sirven desde `/assets/...` y los usa
`src/components/Brand.jsx`. Esta carpeta de origen se conserva sin binarios
duplicados.
