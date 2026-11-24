// Cuentas guardadas en el navegador, una clave por rol. SQLite del navegador se usa como copia cuando carga.
// Cuando exista backend, este módulo se reemplaza por las rutas de perfiles.
import { JEFE_ID } from "./permissions";

export const DIRECTORY_KEYS = { jefe: "bodega-jefes", empleado: "bodega-employees", cliente: "bodega-clients", admin: "bodega-admins" };
const LEGACY_JEFE_KEY = "bodega-jefe";

function readList(storage, key) {
  try {
    const value = JSON.parse(storage.getItem(key));
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

export function mergeProfiles(primary, secondary) {
  const merged = new Map(secondary.filter((profile) => profile?.id).map((profile) => [profile.id, profile]));
  primary.filter((profile) => profile?.id).forEach((profile) => merged.set(profile.id, profile));
  return [...merged.values()];
}

export function readDirectory(storage = localStorage) {
  const saved = Object.values(DIRECTORY_KEYS).flatMap((key) => readList(storage, key));
  let legacy = null;
  try {
    legacy = JSON.parse(storage.getItem(LEGACY_JEFE_KEY));
  } catch {
    legacy = null;
  }
  return legacy?.email ? mergeProfiles(saved, [{ ...legacy, role: "jefe", id: legacy.id || JEFE_ID }]) : saved;
}

export function writeDirectory(profiles, storage = localStorage) {
  Object.entries(DIRECTORY_KEYS).forEach(([role, key]) => storage.setItem(key, JSON.stringify(profiles.filter((profile) => profile.role === role))));
  const legacy = profiles.find((profile) => profile.id === JEFE_ID && profile.role === "jefe");
  if (legacy) storage.setItem(LEGACY_JEFE_KEY, JSON.stringify(legacy));
}

export function findAccount(profiles, email) {
  const needle = String(email || "").trim().toLowerCase();
  return profiles.find((profile) => profile.email?.toLowerCase() === needle) || null;
}
