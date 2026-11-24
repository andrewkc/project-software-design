// Perfil administrador de BodeSmart: consulta tipo Notion (vista por rol, búsqueda, filtros Y, orden múltiple)
// y reglas para crear, editar y eliminar cuentas sin perder historial.
import { fold } from "./textTools";

export const ROLE_LABELS = { jefe: "Jefe de bodega", empleado: "Empleado", cliente: "Cliente", admin: "Administrador" };
const STORE_ROLES = ["jefe", "empleado", "cliente"];
const ID_PREFIX = { jefe: "jefe", empleado: "emp", cliente: "cli", admin: "adm" };

export const FIELDS = [
  { key: "name", label: "Nombre", type: "text" },
  { key: "email", label: "Correo", type: "text" },
  { key: "role", label: "Rol", type: "select" },
  { key: "store", label: "Bodega", type: "text" },
  { key: "activo", label: "Estado", type: "boolean" },
  { key: "creadoEn", label: "Creado", type: "date" },
];

export const OPERATORS = {
  text: [
    { id: "contains", label: "contiene" },
    { id: "not_contains", label: "no contiene" },
    { id: "equals", label: "es" },
    { id: "starts_with", label: "empieza con" },
    { id: "is_empty", label: "está vacío", unary: true },
    { id: "is_not_empty", label: "no está vacío", unary: true },
  ],
  select: [{ id: "is", label: "es" }, { id: "is_not", label: "no es" }],
  boolean: [{ id: "is", label: "es" }],
  date: [
    { id: "before", label: "antes de" },
    { id: "after", label: "después de" },
    { id: "on", label: "es el día" },
    { id: "is_empty", label: "está vacío", unary: true },
    { id: "is_not_empty", label: "no está vacío", unary: true },
  ],
};

const SEARCH_KEYS = ["name", "email", "store"];
const collator = new Intl.Collator("es", { sensitivity: "base", numeric: true });
const isEmpty = (value) => value === null || value === undefined || value === "";

export const fieldOf = (key) => FIELDS.find((field) => field.key === key);
export const operatorOf = (type, id) => OPERATORS[type]?.find((operator) => operator.id === id);

function isComplete(filter) {
  const field = fieldOf(filter.field);
  const operator = field && operatorOf(field.type, filter.operator);
  return Boolean(operator && (operator.unary || !isEmpty(filter.value)));
}

function matchesFilter(row, { field, operator, value: expected }) {
  const value = row[field];
  switch (operator) {
    case "is_empty": return isEmpty(value);
    case "is_not_empty": return !isEmpty(value);
    case "contains": return fold(value ?? "").includes(fold(expected));
    case "not_contains": return !fold(value ?? "").includes(fold(expected));
    case "equals": return fold(value ?? "") === fold(expected);
    case "starts_with": return fold(value ?? "").startsWith(fold(expected));
    case "is": return String(value) === String(expected);
    case "is_not": return String(value) !== String(expected);
    case "before": return !isEmpty(value) && value.slice(0, 10) < expected;
    case "after": return !isEmpty(value) && value.slice(0, 10) > expected;
    case "on": return !isEmpty(value) && value.slice(0, 10) === expected;
    default: return true;
  }
}

function compareValues(first, second) {
  if (typeof first === "boolean" || typeof second === "boolean") return Number(second) - Number(first);
  return collator.compare(String(first), String(second));
}

export function applyQuery(rows, { role, search = "", filters = [], sorts = [] } = {}) {
  const needle = fold(search.trim());
  const active = filters.filter(isComplete);
  const result = rows.filter((row) => (!role || row.role === role)
    && (!needle || SEARCH_KEYS.some((key) => fold(row[key] ?? "").includes(needle)))
    && active.every((filter) => matchesFilter(row, filter)));
  if (!sorts.length) return result;
  return result.sort((left, right) => {
    for (const { field, direction } of sorts) {
      const first = left[field];
      const second = right[field];
      // Los vacíos quedan al final en cualquier dirección, como en Notion.
      if (isEmpty(first) || isEmpty(second)) {
        if (isEmpty(first) && isEmpty(second)) continue;
        return isEmpty(first) ? 1 : -1;
      }
      const order = compareValues(first, second);
      if (order) return direction === "desc" ? -order : order;
    }
    return 0;
  });
}

export function validateProfile(draft, profiles, { editingId = null, selfId = null } = {}) {
  const email = String(draft.email || "").trim().toLowerCase();
  const store = String(draft.store || "").trim();
  if (!String(draft.nombres || "").trim()) return "Ingresa los nombres.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return "Ingresa un correo válido.";
  if (profiles.some((profile) => profile.id !== editingId && profile.email?.toLowerCase() === email)) return "Ya existe una cuenta con ese correo.";
  if (STORE_ROLES.includes(draft.role) && !store) return "Indica la bodega.";
  const password = String(draft.password || "");
  if ((!editingId || password) && password.length < 8) return "La contraseña debe tener al menos 8 caracteres.";
  if (editingId && editingId === selfId) {
    if (draft.role !== "admin") return "No puedes cambiar tu propio rol.";
    if (draft.activo === false) return "No puedes desactivar tu propia cuenta.";
  }
  if (draft.role === "jefe" && draft.activo !== false
    && profiles.some((profile) => profile.id !== editingId && profile.role === "jefe" && profile.activo !== false && fold(profile.store || "") === fold(store))) {
    return "Esa bodega ya tiene un jefe activo.";
  }
  return null;
}

export function buildProfile(draft, existing, { now = new Date().toISOString(), stamp = Date.now() } = {}) {
  const nombres = String(draft.nombres || "").trim();
  const apellidos = String(draft.apellidos || "").trim();
  const activo = draft.activo !== false;
  const profile = {
    ...(existing || {}),
    id: existing?.id || `${ID_PREFIX[draft.role]}-${stamp}`,
    role: draft.role,
    nombres,
    apellidos,
    name: `${nombres} ${apellidos}`.trim(),
    email: String(draft.email).trim().toLowerCase(),
    store: draft.role === "admin" ? "" : String(draft.store || "").trim(),
    password: String(draft.password || "") || existing?.password || "",
    activo,
    creadoEn: existing?.creadoEn || now,
  };
  if (existing) profile.revocadoEn = activo ? "" : existing.revocadoEn || now;
  return profile;
}

export function historyCount(profile, { products = [], movements = [], orders = [] } = {}) {
  return products.filter((product) => product.creadoPor === profile.id).length
    + movements.filter((movement) => movement.responsable === profile.id).length
    + orders.filter((order) => order.clienteId === profile.id || order.atendidoPor === profile.id).length;
}

export function deleteBlockReason(profile, history, selfId) {
  if (profile.id === selfId) return "No puedes eliminar tu propia cuenta.";
  if (historyCount(profile, history) > 0) return "Esta cuenta tiene historial de productos, ventas o pedidos. Desactívala para conservarlo.";
  return null;
}
