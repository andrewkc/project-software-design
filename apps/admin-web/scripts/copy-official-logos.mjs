import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

// Los logos oficiales viven en operations-web. Los copiamos tal cual a
// admin-web para que el panel no dependa de otra carpeta en runtime.
const here = dirname(fileURLToPath(import.meta.url));
const source = resolve(here, "../../operations-web/src/assets");
const target = resolve(here, "../public/assets");
const logos = ["BodeSmart-Logo.png", "BodeSmart-Mobile-Logo.png"];

if (!existsSync(source)) {
  console.warn(`[bodesmart-logos] No existe ${source}; se conservan los logos ya copiados en ${target}.`);
  process.exit(0);
}

mkdirSync(target, { recursive: true });
for (const logo of logos) {
  const from = resolve(source, logo);
  if (!existsSync(from)) {
    console.warn(`[bodesmart-logos] Falta ${from}; se conserva la copia anterior si existe.`);
    continue;
  }
  copyFileSync(from, resolve(target, logo));
  console.log(`[bodesmart-logos] ${logo} -> admin-web/public/assets/${logo}`);
}
