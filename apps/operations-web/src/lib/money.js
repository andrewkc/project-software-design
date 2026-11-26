export const money = (value) => new Intl.NumberFormat("es-PE", {
  style: "currency",
  currency: "PEN",
}).format(Number(value) || 0);
