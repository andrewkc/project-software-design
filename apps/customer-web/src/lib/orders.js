// Pedido del cliente: es una solicitud. El stock solo se descuenta cuando el personal lo acepta como venta.
import { localToday, registerSale, saleBlockReason } from "./sales";

export class OrderError extends Error {}

const STAFF_ROLES = ["jefe", "empleado"];
const money = (value) => Math.round((value + Number.EPSILON) * 100) / 100;
const newestFirst = (list) => [...list].sort((first, second) => String(second.creadoEn).localeCompare(String(first.creadoEn)));

function assertStaff(user) {
  if (!STAFF_ROLES.includes(user?.role)) throw new OrderError("Solo el personal de la bodega atiende pedidos.");
}

function assertPending(order) {
  if (order.estado !== "pendiente") throw new OrderError("Este pedido ya fue atendido.");
}

export function createOrder(products, cart, user, { now = new Date().toISOString(), today = localToday(), id = `ped-${Date.now()}` } = {}) {
  if (user?.role !== "cliente") throw new OrderError("Solo un cliente puede enviar pedidos.");
  if (!cart.length) throw new OrderError("Tu pedido está vacío.");
  const lineas = cart.map(({ productId, quantity }) => {
    const product = products.find((item) => item.id === productId);
    if (!product || saleBlockReason(product, today)) throw new OrderError(`${product?.name || "Un producto"} ya no está disponible.`);
    if (!(quantity > 0)) throw new OrderError("Cada producto necesita una cantidad mayor que cero.");
    if (quantity > Number(product.stock)) throw new OrderError(`Solo quedan ${product.stock} ${product.unit} de ${product.name}.`);
    const precio = Number(product.price);
    return { productoId: product.id, productoNombre: product.name, cantidad: quantity, unidad: product.unit, precio, subtotal: money(precio * quantity) };
  });
  return { id, store: user.store, clienteId: user.id, clienteNombre: user.name, creadoEn: now, estado: "pendiente", total: money(lineas.reduce((total, line) => total + line.subtotal, 0)), lineas };
}

// Reutiliza registerSale: valida vencidos, desactivados y stock con los datos más recientes.
export function acceptOrder(order, products, user, { now = new Date().toISOString(), today = localToday(), id } = {}) {
  assertPending(order);
  const cart = order.lineas.map((line) => ({ productId: line.productoId, quantity: line.cantidad }));
  const sale = registerSale(products, cart, user, { now, today, ...(id ? { id } : {}) });
  const movement = { ...sale.movement, pedidoId: order.id, clienteNombre: order.clienteNombre };
  return {
    products: sale.products,
    movement,
    order: { ...order, estado: "aceptado", atendidoPor: user.id, atendidoPorNombre: user.name, atendidoEn: now, ventaId: movement.id },
  };
}

export function rejectOrder(order, user, motivo, { now = new Date().toISOString() } = {}) {
  assertStaff(user);
  assertPending(order);
  const reason = String(motivo || "").trim();
  if (!reason) throw new OrderError("Indica el motivo del rechazo.");
  return { ...order, estado: "rechazado", motivoRechazo: reason, atendidoPor: user.id, atendidoPorNombre: user.name, atendidoEn: now };
}

export function cancelOrder(order, user, { now = new Date().toISOString() } = {}) {
  if (user?.id !== order.clienteId) throw new OrderError("Solo quien hizo el pedido puede cancelarlo.");
  assertPending(order);
  return { ...order, estado: "cancelado", canceladoEn: now };
}

export function visibleOrders(orders, user) {
  if (user?.role === "cliente") return newestFirst(orders.filter((order) => order.clienteId === user.id));
  if (STAFF_ROLES.includes(user?.role)) return newestFirst(orders.filter((order) => !user.store || order.store === user.store));
  return [];
}

export function pendingOrders(orders, user) {
  return visibleOrders(orders, user).filter((order) => order.estado === "pendiente");
}
