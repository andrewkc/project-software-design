export const JEFE_ID = "user-jefe";

const OTHER_ROLES = ["empleado", "cliente", "admin"];
const ID_PREFIX = { empleado: "emp", cliente: "cli", admin: "adm" };

export function withUserDefaults(user) {
  if (!user) return null;
  const role = OTHER_ROLES.includes(user.role) ? user.role : "jefe";
  return {
    ...user,
    id: user.id || (role === "jefe" ? JEFE_ID : `${ID_PREFIX[role]}-${Date.now()}`),
    role,
    // El administrador es de BodeSmart como empresa: no pertenece a ninguna bodega.
    store: role === "admin" ? "" : user.store || "Bodega San Martín",
  };
}

export function withProductDefaults(product) {
  return {
    ...product,
    creadoPor: product.creadoPor || JEFE_ID,
    bloqueado: Boolean(product.bloqueado),
    bloqueadoPor: product.bloqueadoPor || null,
    activo: product.activo !== false,
  };
}

export function isJefe(user) {
  return !user || !OTHER_ROLES.includes(user.role);
}

export function isCliente(user) {
  return user?.role === "cliente";
}

export function isAdmin(user) {
  return user?.role === "admin";
}

export function currentUserId(user) {
  return user?.id || JEFE_ID;
}

export function canEditProduct(product, user) {
  if (!product || product.activo === false || isCliente(user) || isAdmin(user)) return false;
  if (isJefe(user)) return true;
  return product.creadoPor === currentUserId(user) && !product.bloqueado;
}
