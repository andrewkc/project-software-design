import { describe, expect, test, vi } from "vitest";
import { customerCatalog, stockChanges, subscribeToKeys } from "./liveStock";
import { canEditProduct, isCliente, isJefe, withUserDefaults } from "./permissions";

const today = "2026-11-23";
const products = [
  { id: 1, name: "Leche", category: "Lácteos", icon: "🥛", stock: 8, unit: "unid.", price: 4.5, expires: "2026-12-20", activo: true, creadoPor: "emp-7", bloqueado: true, costo: 3 },
  { id: 2, name: "Arroz", category: "Abarrotes", icon: "🍚", stock: 5, unit: "unid.", price: 4.2, expires: "", activo: true },
  { id: 3, name: "Atún", category: "Conservas", icon: "🥫", stock: 0, unit: "unid.", price: 6.4, expires: "", activo: true },
  { id: 4, name: "Yogurt", category: "Lácteos", icon: "🥛", stock: 5, unit: "unid.", price: 3.8, expires: "2026-11-22", activo: true },
  { id: 5, name: "Lejía", category: "Limpieza", icon: "🧼", stock: 5, unit: "unid.", price: 4.9, expires: "", activo: false },
];

describe("customerCatalog", () => {
  test("oculta productos vencidos y desactivados", () => {
    expect(customerCatalog(products, today).map((item) => item.id)).toEqual([1, 2, 3]);
  });
  test("clasifica disponibilidad", () => {
    expect(customerCatalog(products, today).map((item) => item.availability)).toEqual(["available", "low", "out"]);
  });
  test("no expone datos internos", () => {
    const [item] = customerCatalog(products, today);
    expect(Object.keys(item).sort()).toEqual(["availability", "category", "expires", "icon", "id", "name", "price", "stock", "unit"]);
  });
});

describe("stockChanges", () => {
  test("devuelve solo los productos cuyo stock cambió", () => {
    const next = [{ ...products[0], stock: 6 }, products[1]];
    expect(stockChanges(products, next)).toEqual({ 1: -2 });
  });
  test("ignora productos nuevos y listas iguales", () => {
    expect(stockChanges(products.slice(0, 1), products)).toEqual({});
    expect(stockChanges(products, products)).toEqual({});
  });
});

describe("subscribeToKeys", () => {
  function setup() {
    const target = new EventTarget();
    const onChange = vi.fn();
    return { target, onChange, stop: subscribeToKeys(["bodega-products"], onChange, target) };
  }
  const send = (target, key, newValue) => {
    const event = new Event("storage");
    Object.assign(event, { key, newValue });
    target.dispatchEvent(event);
  };
  test("avisa cuando otra pestaña cambia una clave vigilada", () => {
    const { target, onChange } = setup();
    send(target, "bodega-products", JSON.stringify([{ id: 1 }]));
    expect(onChange).toHaveBeenCalledWith("bodega-products", [{ id: 1 }]);
  });
  test("ignora otras claves, borrados y JSON roto", () => {
    const { target, onChange } = setup();
    send(target, "otra", "[]");
    send(target, "bodega-products", null);
    send(target, "bodega-products", "{roto");
    expect(onChange).not.toHaveBeenCalled();
  });
  test("deja de escuchar al cancelar", () => {
    const { target, onChange, stop } = setup();
    stop();
    send(target, "bodega-products", "[]");
    expect(onChange).not.toHaveBeenCalled();
  });
});

describe("rol cliente", () => {
  const cliente = withUserDefaults({ id: "c1", role: "cliente", name: "Cliente", store: "Bodega X" });
  test("se conserva y no se confunde con jefe", () => {
    expect(cliente.role).toBe("cliente");
    expect(isCliente(cliente)).toBe(true);
    expect(isJefe(cliente)).toBe(false);
  });
  test("no puede editar productos", () => {
    expect(canEditProduct({ ...products[1], creadoPor: "c1" }, cliente)).toBe(false);
  });
});
