import { localToday, saleBlockReason } from "./sales";

const LOW_STOCK = 5;

function availability(stock) {
  if (Number(stock) <= 0) return "out";
  return Number(stock) <= LOW_STOCK ? "low" : "available";
}

// Lista explícita de campos: el cliente nunca recibe autor, candado ni datos internos.
export function customerCatalog(products, today = localToday()) {
  return products
    .filter((product) => !["Vencido", "Desactivado"].includes(saleBlockReason(product, today)))
    .map(({ id, name, category, icon, stock, unit, price, expires }) => ({ id, name, category, icon, stock, unit, price, expires, availability: availability(stock) }));
}

export function stockChanges(previous, next) {
  const before = new Map(previous.map((product) => [product.id, Number(product.stock)]));
  return Object.fromEntries(next
    .filter((product) => before.has(product.id) && before.get(product.id) !== Number(product.stock))
    .map((product) => [product.id, Math.round((Number(product.stock) - before.get(product.id)) * 1000) / 1000]));
}

// El evento storage solo llega a las otras pestañas. Cuando exista backend se reemplaza por su canal en vivo.
export function subscribeToKeys(keys, onChange, target = window) {
  function handleStorage(event) {
    if (!keys.includes(event.key) || event.newValue === null) return;
    try {
      onChange(event.key, JSON.parse(event.newValue));
    } catch {
      // Un valor corrupto no debe tirar la pantalla; se conserva el último estado válido.
    }
  }
  target.addEventListener("storage", handleStorage);
  return () => target.removeEventListener("storage", handleStorage);
}
