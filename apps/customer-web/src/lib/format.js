// Formatos compartidos por la caja de ventas y el carrito del cliente.
export const soles = (value) => `S/ ${Number(value || 0).toFixed(2)}`;

// Lo que se vende por peso o volumen avanza de medio en medio; lo demás, de uno en uno.
export const stepFor = (unit) => (["kg", "litro"].includes(unit) ? 0.5 : 1);

export const timeLabel = (value) => new Date(value).toLocaleString("es-PE", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
