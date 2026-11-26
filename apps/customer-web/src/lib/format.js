export const money = (value) => `S/ ${Number(value || 0).toFixed(2)}`;

export function dateLabel(value) {
  if (!value) return "sin fecha de vencimiento";
  return new Date(`${value}T12:00:00Z`).toLocaleDateString("es-PE", {
    timeZone: "America/Lima", day: "numeric", month: "long",
  });
}

export const orderTitle = (state) => ({
  pagado: "¡Compra confirmada!",
  pendiente: "Completa tu compra",
  pago_en_revision: "Pago en revisión",
  rechazado: "Pago rechazado",
  expirado: "Este pedido venció",
})[state] || "Estado del pedido";

export const orderSummary = (state) => ({
  pagado: "Tu pago fue aprobado y el inventario quedó actualizado.",
  pendiente: "Reservamos tus productos por diez minutos mientras completas el pago.",
  pago_en_revision: "El pago se acreditó después de perderse la reserva. La bodega debe revisar este caso; no descontamos otros productos.",
  rechazado: "No se aprobó el pago. La reserva se liberó y puedes iniciar otro pedido.",
  expirado: "La reserva se liberó. Puedes iniciar otro pedido desde las ofertas.",
})[state] || "Consulta el estado de tu pedido.";

export const orderStatus = (state) => ({
  pagado: "Pago aprobado",
  pendiente: "Pendiente de pago",
  pago_en_revision: "Pago en revisión",
  rechazado: "Pago rechazado",
  expirado: "Reserva vencida",
})[state] || state;

export function fullName(user) {
  const name = [user?.nombres, user?.apellidos].filter(Boolean).join(" ").trim();
  return name || user?.nombre || user?.email || "Cliente BodeSmart";
}

export function shortName(user) {
  const parts = fullName(user).split(/\s+/).filter(Boolean);
  return [parts[0], parts[parts.length - 1]].filter(Boolean).join(" ");
}

export function initial(user) {
  return shortName(user).charAt(0).toUpperCase() || "C";
}
