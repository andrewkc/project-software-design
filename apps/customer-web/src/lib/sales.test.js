import { describe, expect, test } from "vitest";
import { addToCart, cartTotal, registerSale, SaleError, saleBlockReason, setCartQuantity } from "./sales";

const today = "2026-11-23";
const now = "2026-11-23T15:00:00.000Z";
const user = { id: "emp-1", role: "empleado", name: "Ana Torres" };
const products = [
  { id: 1, name: "Leche", stock: 8, unit: "unid.", price: 4.5, expires: "2026-12-20", activo: true },
  { id: 2, name: "Arroz", stock: 3, unit: "unid.", price: 4.2, expires: "", activo: true },
  { id: 3, name: "Yogurt", stock: 5, unit: "unid.", price: 3.8, expires: "2026-11-22", activo: true },
  { id: 4, name: "Lejía", stock: 5, unit: "unid.", price: 4.9, expires: "", activo: false },
  { id: 5, name: "Plátano", stock: 2.5, unit: "kg", price: 3.5, expires: "2026-11-23", activo: true },
  { id: 6, name: "Atún", stock: 0, unit: "unid.", price: 6.4, expires: "", activo: true },
];
const sale = (cart, list = products) => registerSale(list, cart, user, { now, today, id: "mov-1" });

describe("saleBlockReason", () => {
  test("permite productos activos, con stock y sin vencer", () => {
    expect(saleBlockReason(products[0], today)).toBeNull();
    expect(saleBlockReason(products[1], today)).toBeNull();
  });
  test("el día de vencimiento todavía se puede vender", () => {
    expect(saleBlockReason(products[4], today)).toBeNull();
  });
  test("bloquea vencido, desactivado y sin stock", () => {
    expect(saleBlockReason(products[2], today)).toBe("Vencido");
    expect(saleBlockReason(products[3], today)).toBe("Desactivado");
    expect(saleBlockReason(products[5], today)).toBe("Sin stock");
  });
});

describe("cesta", () => {
  test("agregar acumula la cantidad del mismo producto", () => {
    expect(addToCart(addToCart([], 1), 1, 2)).toEqual([{ productId: 1, quantity: 3 }]);
  });
  test("cantidad cero o inválida quita la línea", () => {
    const cart = [{ productId: 1, quantity: 2 }, { productId: 2, quantity: 1 }];
    expect(setCartQuantity(cart, 1, 0)).toEqual([{ productId: 2, quantity: 1 }]);
    expect(setCartQuantity(cart, 1, Number.NaN)).toEqual([{ productId: 2, quantity: 1 }]);
  });
  test("el total usa el precio actual y redondea a céntimos", () => {
    expect(cartTotal([{ productId: 1, quantity: 3 }, { productId: 2, quantity: 1 }], products)).toBe(17.7);
  });
});

describe("registerSale", () => {
  test("descuenta stock una vez y deja un movimiento trazable", () => {
    const result = sale([{ productId: 1, quantity: 2 }, { productId: 2, quantity: 3 }]);
    expect(result.products.find((item) => item.id === 1).stock).toBe(6);
    expect(result.products.find((item) => item.id === 2).stock).toBe(0);
    expect(result.movement).toMatchObject({
      id: "mov-1", fechaHora: now, tipo: "salida", motivo: "Venta", total: 21.6,
      responsable: "emp-1", responsableNombre: "Ana Torres",
    });
    expect(result.movement.detalles[0]).toEqual({
      productoId: 1, productoNombre: "Leche", loteId: "lote-1", loteCodigo: "INICIAL",
      cantidad: 2, unidad: "unid.", importeUnitario: 4.5, subtotal: 9,
    });
  });
  test("no modifica la lista original", () => {
    const copy = structuredClone(products);
    sale([{ productId: 1, quantity: 1 }]);
    expect(products).toEqual(copy);
  });
  test("une líneas repetidas antes de validar stock", () => {
    expect(() => sale([{ productId: 2, quantity: 2 }, { productId: 2, quantity: 2 }])).toThrow(/Stock insuficiente para Arroz/);
  });
  test("admite vender exactamente todo el stock, incluso decimal", () => {
    expect(sale([{ productId: 5, quantity: 2.5 }]).products.find((item) => item.id === 5).stock).toBe(0);
  });
  test("evita residuos de punto flotante", () => {
    const list = [{ ...products[4], stock: 0.3 }];
    expect(sale([{ productId: 5, quantity: 0.1 }], list).products[0].stock).toBe(0.2);
  });
  test.each([
    ["vacía", [], /cesta está vacía/],
    ["cantidad cero", [{ productId: 1, quantity: 0 }], /cantidad/i],
    ["cantidad negativa", [{ productId: 1, quantity: -1 }], /cantidad/i],
    ["producto inexistente", [{ productId: 99, quantity: 1 }], /no existe/],
    ["vencido", [{ productId: 3, quantity: 1 }], /Yogurt está vencido/],
    ["desactivado", [{ productId: 4, quantity: 1 }], /Lejía está desactivado/],
    ["sobre el stock", [{ productId: 2, quantity: 4 }], /Stock insuficiente para Arroz/],
  ])("rechaza venta %s", (_name, cart, message) => {
    expect(() => sale(cart)).toThrow(SaleError);
    expect(() => sale(cart)).toThrow(message);
  });
  test("una línea inválida rechaza toda la venta", () => {
    expect(() => sale([{ productId: 1, quantity: 1 }, { productId: 3, quantity: 1 }])).toThrow(SaleError);
    expect(products[0].stock).toBe(8);
  });
  test("exige un responsable", () => {
    expect(() => registerSale(products, [{ productId: 1, quantity: 1 }], null, { now, today })).toThrow(/responsable/);
  });
  test("un cliente no puede registrar ventas", () => {
    expect(() => registerSale(products, [{ productId: 1, quantity: 1 }], { id: "c1", role: "cliente", name: "C" }, { now, today })).toThrow(/responsable/);
  });
});
