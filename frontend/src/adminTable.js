// Notion-style query over admin profile rows: view role, free search, AND filters and multi-column sort.

export const ROLE_LABELS = {
  ADMIN: "Administrador",
  OWNER: "Jefe de bodega",
  EMPLOYEE: "Empleado",
  CUSTOMER: "Cliente",
};

export const FIELDS = [
  { key: "name", label: "Nombre", type: "text" },
  { key: "email", label: "Correo", type: "text" },
  { key: "role", label: "Rol", type: "select" },
  { key: "store_name", label: "Bodega", type: "text" },
  { key: "is_active", label: "Estado", type: "boolean" },
  { key: "last_login", label: "Último acceso", type: "date" },
  { key: "created_at", label: "Creado", type: "date" },
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
  select: [
    { id: "is", label: "es" },
    { id: "is_not", label: "no es" },
  ],
  boolean: [{ id: "is", label: "es" }],
  date: [
    { id: "before", label: "antes de" },
    { id: "after", label: "después de" },
    { id: "on", label: "es el día" },
    { id: "is_empty", label: "está vacío", unary: true },
    { id: "is_not_empty", label: "no está vacío", unary: true },
  ],
};

const SEARCH_KEYS = ["name", "email", "store_name"];
const collator = new Intl.Collator("es", { sensitivity: "base", numeric: true });

export function fieldOf(key) {
  return FIELDS.find((field) => field.key === key);
}

export function operatorOf(type, id) {
  return OPERATORS[type]?.find((operator) => operator.id === id);
}

function fold(value) {
  return String(value ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

function isEmpty(value) {
  return value === null || value === undefined || value === "";
}

function isComplete(filter) {
  const field = fieldOf(filter.field);
  const operator = field && operatorOf(field.type, filter.operator);
  return Boolean(operator && (operator.unary || !isEmpty(filter.value)));
}

export function matchesFilter(row, filter) {
  const value = row[filter.field];
  switch (filter.operator) {
    case "is_empty": return isEmpty(value);
    case "is_not_empty": return !isEmpty(value);
    case "contains": return fold(value).includes(fold(filter.value));
    case "not_contains": return !fold(value).includes(fold(filter.value));
    case "equals": return fold(value) === fold(filter.value);
    case "starts_with": return fold(value).startsWith(fold(filter.value));
    case "is": return String(value) === String(filter.value);
    case "is_not": return String(value) !== String(filter.value);
    case "before": return !isEmpty(value) && value.slice(0, 10) < filter.value;
    case "after": return !isEmpty(value) && value.slice(0, 10) > filter.value;
    case "on": return !isEmpty(value) && value.slice(0, 10) === filter.value;
    default: return true;
  }
}

function compareValues(a, b) {
  if (typeof a === "boolean" || typeof b === "boolean") return Number(b) - Number(a);
  return collator.compare(String(a), String(b));
}

export function applyQuery(rows, { role, search = "", filters = [], sorts = [] } = {}) {
  const needle = fold(search.trim());
  const active = filters.filter(isComplete);
  const result = rows.filter((row) => (!role || row.role === role)
    && (!needle || SEARCH_KEYS.some((key) => fold(row[key]).includes(needle)))
    && active.every((filter) => matchesFilter(row, filter)));
  if (!sorts.length) return result;
  return result.sort((left, right) => {
    for (const { field, direction } of sorts) {
      const a = left[field];
      const b = right[field];
      // Empty values stay at the bottom whatever the direction, as in Notion.
      if (isEmpty(a) || isEmpty(b)) {
        if (isEmpty(a) && isEmpty(b)) continue;
        return isEmpty(a) ? 1 : -1;
      }
      const order = compareValues(a, b);
      if (order) return direction === "desc" ? -order : order;
    }
    return 0;
  });
}
