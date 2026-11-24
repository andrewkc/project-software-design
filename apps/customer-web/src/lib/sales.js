// CU-05: venta atómica en el navegador. Valida toda la cesta antes de descontar (RN-03 a RN-06).

export class SaleError extends Error {}

const STAFF_ROLES = ["jefe", "empleado"];
const money = (value) => Math.round((value + Number.EPSILON) * 100) / 100;
const quantityValue = (value) => Math.round((value + Number.EPSILON) * 1000) / 1000;

export function localToday(date = new Date()) {
  return date.toLocaleDateString("en-CA");
}

export function saleBlockReason(product, today = localToday()) {
  if (product.activo === false) return "Desactivado";
  if (product.expires && product.expires < today) return "Vencido";
  if (Number(product.stock) <= 0) return "Sin stock";
  return null;
}

export function addToCart(cart, productId, quantity = 1) {
  const current = cart.find((line) => line.productId === productId);
  if (!current) return [...cart, { productId, quantity }];
  return cart.map((line) => line === current ? { ...line, quantity: quantityValue(line.quantity + quantity) } : line);
}

// Agrega sin pasar el stock: si no alcanza, completa hasta el máximo y avisa con capped.
export function addWithinStock(cart, product, quantity) {
  const inCart = cart.find((line) => line.productId === product.id)?.quantity || 0;
  const stock = Number(product.stock);
  if (inCart + quantity <= stock) return { cart: addToCart(cart, product.id, quantity), capped: false };
  return { cart: stock > inCart ? addToCart(cart, product.id, quantityValue(stock - inCart)) : cart, capped: true };
}

export function setCartQuantity(cart, productId, quantity) {
  if (!Number.isFinite(quantity) || quantity <= 0) return cart.filter((line) => line.productId !== productId);
  return cart.map((line) => line.productId === productId ? { ...line, quantity } : line);
}

export function cartTotal(cart, products) {
  return money(cart.reduce((total, line) => {
    const product = products.find((item) => item.id === line.productId);
    return total + (product ? Number(product.price) * line.quantity : 0);
  }, 0));
}

function mergedLines(cart) {
  const merged = new Map();
  for (const { productId, quantity } of cart) {
    if (!Number.isFinite(quantity) || quantity <= 0) throw new SaleError("Cada producto necesita una cantidad mayor que cero.");
    merged.set(productId, quantityValue((merged.get(productId) || 0) + quantity));
  }
  return merged;
}

function assertSellable(product, quantity, today) {
  const reason = saleBlockReason(product, today);
  if (reason === "Vencido") throw new SaleError(`${product.name} está vencido; registra una merma.`);
  if (reason === "Desactivado") throw new SaleError(`${product.name} está desactivado.`);
  if (reason === "Sin stock" || quantity > Number(product.stock)) throw new SaleError(`Stock insuficiente para ${product.name}.`);
}

export function registerSale(products, cart, user, { now = new Date().toISOString(), today = localToday(), id = `mov-${Date.now()}` } = {}) {
  if (!user?.id || !STAFF_ROLES.includes(user.role)) throw new SaleError("La venta necesita un responsable de la bodega.");
  if (!cart.length) throw new SaleError("La cesta está vacía.");
  const lines = mergedLines(cart);
  const detalles = [];
  for (const [productId, cantidad] of lines) {
    const product = products.find((item) => item.id === productId);
    if (!product) throw new SaleError("Uno de los productos ya no existe.");
    assertSellable(product, cantidad, today);
    const importeUnitario = Number(product.price);
    // El prototipo maneja un lote implícito por producto, como el lote INICIAL del backend.
    detalles.push({ productoId: product.id, productoNombre: product.name, loteId: `lote-${product.id}`, loteCodigo: "INICIAL", cantidad, unidad: product.unit, importeUnitario, subtotal: money(cantidad * importeUnitario) });
  }
  return {
    products: products.map((product) => lines.has(product.id) ? { ...product, stock: quantityValue(Number(product.stock) - lines.get(product.id)) } : product),
    movement: { id, fechaHora: now, tipo: "salida", motivo: "Venta", total: money(detalles.reduce((total, item) => total + item.subtotal, 0)), responsable: user.id, responsableNombre: user.name, detalles },
  };
}
