export const JEFE_ID = "user-jefe";

export function withUserDefaults(user) {
  if (!user) return null;
  const role = ["empleado", "cliente"].includes(user.role) ? user.role : "jefe";
  return {
    ...user,
    id: user.id || (role === "jefe" ? JEFE_ID : `${role === "empleado" ? "emp" : "cli"}-${Date.now()}`),
    role,
    store: user.store || "Bodega San Martín",
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
  return !user || !["empleado", "cliente"].includes(user.role);
}

export function isCliente(user) {
  return user?.role === "cliente";
}

export function currentUserId(user) {
  return user?.id || JEFE_ID;
}

export function canEditProduct(product, user) {
  if (!product || product.activo === false || isCliente(user)) return false;
  if (isJefe(user)) return true;
  return product.creadoPor === currentUserId(user) && !product.bloqueado;
}
