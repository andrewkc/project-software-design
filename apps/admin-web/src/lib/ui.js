export const ROLE_LABELS = {
  admin: "Admin",
  jefe: "Jefe",
  empleado: "Empleado",
  cliente: "Cliente",
};

export const ROLE_OPTIONS = Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }));

export function displayName(user) {
  const full = String(user?.nombre || [user?.nombres, user?.apellidos].filter(Boolean).join(" ")).trim();
  return full || "Administrador";
}

export function initials(name) {
  const parts = String(name || "Admin").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return `${parts[0].charAt(0)}${parts[parts.length - 1].charAt(0)}`.toUpperCase();
}
