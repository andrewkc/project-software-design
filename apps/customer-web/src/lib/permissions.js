export const JEFE_ID = "user-jefe";

export function withUserDefaults(user) {
  if (!user) return null;
  const role = user.role === "empleado" ? "empleado" : "jefe";
  return {
    ...user,
    id: user.id || (role === "empleado" ? `emp-${Date.now()}` : JEFE_ID),
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
  return !user || user.role !== "empleado";
}

export function currentUserId(user) {
  return user?.id || JEFE_ID;
}

export function canEditProduct(product, user) {
  if (!product || product.activo === false) return false;
  if (isJefe(user)) return true;
  return product.creadoPor === currentUserId(user) && !product.bloqueado;
}
