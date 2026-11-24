// @vitest-environment jsdom
import React from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { CustomerStockPage } from "./CustomerStockPage";

const user = { id: "c1", role: "cliente", name: "Diego Paz", store: "Bodega San Martín" };
const products = [
  { id: 1, name: "Leche Gloria", category: "Lácteos", icon: "🥛", stock: 8, unit: "unid.", price: 4.5, expires: "2099-01-01", activo: true, creadoPor: "emp-secreto" },
  { id: 2, name: "Arroz extra", category: "Abarrotes", icon: "🍚", stock: 3, unit: "unid.", price: 4.2, expires: "", activo: true },
  { id: 3, name: "Atún", category: "Conservas", icon: "🥫", stock: 0, unit: "unid.", price: 6.4, expires: "", activo: true },
  { id: 4, name: "Yogurt vencido", category: "Lácteos", icon: "🥛", stock: 5, unit: "unid.", price: 3.8, expires: "2020-01-01", activo: true },
  { id: 5, name: "Lejía oculta", category: "Limpieza", icon: "🧼", stock: 5, unit: "unid.", price: 4.9, expires: "", activo: false },
];
const page = (list) => <CustomerStockPage products={list} user={user} />;
const tile = (name) => screen.getByRole("article", { name });

afterEach(cleanup);

test("muestra la bodega vinculada y solo productos que se pueden comprar", () => {
  render(page(products));
  expect(screen.getByText(/Bodega San Martín/)).toBeTruthy();
  expect(screen.getAllByRole("article")).toHaveLength(3);
  expect(screen.queryByText("Yogurt vencido")).toBeNull();
  expect(screen.queryByText("Lejía oculta")).toBeNull();
  expect(document.body.textContent).not.toContain("emp-secreto");
});

test("cada cuadro muestra stock, precio y disponibilidad", () => {
  render(page(products));
  expect(within(tile("Leche Gloria")).getByText("8")).toBeTruthy();
  expect(within(tile("Leche Gloria")).getByText("S/ 4.50")).toBeTruthy();
  expect(within(tile("Arroz extra")).getByText("Últimas unidades")).toBeTruthy();
  expect(within(tile("Atún")).getByText("Agotado")).toBeTruthy();
});

test("actualiza el cuadro en vivo y marca el cambio", () => {
  const { rerender } = render(page(products));
  rerender(page(products.map((item) => item.id === 1 ? { ...item, stock: 6 } : item)));
  const card = tile("Leche Gloria");
  expect(within(card).getByText("6")).toBeTruthy();
  expect(within(card).getByText("-2")).toBeTruthy();
  expect(card.className).toContain("stock-tile-changed");
  expect(screen.getByRole("status").textContent).toContain("Leche Gloria: quedan 6");
  expect(tile("Arroz extra").className).not.toContain("stock-tile-changed");
});

test("busca y filtra por categoría", () => {
  render(page(products));
  fireEvent.change(screen.getByLabelText("Buscar en la bodega"), { target: { value: "arroz" } });
  expect(screen.getAllByRole("article")).toHaveLength(1);
  fireEvent.change(screen.getByLabelText("Buscar en la bodega"), { target: { value: "" } });
  fireEvent.click(screen.getByRole("button", { name: "Conservas" }));
  expect(screen.getAllByRole("article").map((item) => item.getAttribute("aria-label"))).toEqual(["Atún"]);
});

test("el cliente no tiene acciones de venta ni edición", () => {
  render(page(products));
  expect(screen.queryByRole("button", { name: /Editar|Registrar/ })).toBeNull();
});

describe("carrito del cliente", () => {
  const cart = (props = {}) => {
    const onPlaceOrder = vi.fn(() => ({ ok: true }));
    const onCancelOrder = vi.fn();
    const view = render(<CustomerStockPage products={products} user={user} orders={[]} onPlaceOrder={onPlaceOrder} onCancelOrder={onCancelOrder} {...props} />);
    return { onPlaceOrder, onCancelOrder, ...view };
  };
  const add = (name) => fireEvent.click(screen.getByRole("button", { name: `Agregar ${name} al pedido` }));

  beforeEach(() => localStorage.clear());

  test("arma el pedido, calcula el total y lo envía a la bodega", () => {
    const { onPlaceOrder } = cart();
    add("Leche Gloria"); add("Leche Gloria"); add("Arroz extra");
    expect(screen.getByTestId("order-total").textContent).toContain("13.20");
    fireEvent.click(screen.getByRole("button", { name: "Enviar pedido" }));
    expect(onPlaceOrder).toHaveBeenCalledWith([{ productId: 1, quantity: 2 }, { productId: 2, quantity: 1 }]);
    expect(screen.getByText("Tu pedido está vacío")).toBeTruthy();
  });

  test("no deja pedir productos agotados ni más del stock", () => {
    cart();
    expect(screen.getByRole("button", { name: "Atún agotado" }).disabled).toBe(true);
    add("Arroz extra"); add("Arroz extra"); add("Arroz extra"); add("Arroz extra");
    expect(screen.getByLabelText("Cantidad de Arroz extra").value).toBe("3");
    expect(screen.getByRole("alert").textContent).toContain("Solo quedan 3");
  });

  test("si el stock baja en vivo ajusta el pedido y avisa", () => {
    const { rerender, onPlaceOrder, onCancelOrder } = cart();
    add("Arroz extra"); add("Arroz extra"); add("Arroz extra");
    rerender(<CustomerStockPage products={products.map((item) => item.id === 2 ? { ...item, stock: 1 } : item)} user={user} orders={[]} onPlaceOrder={onPlaceOrder} onCancelOrder={onCancelOrder} />);
    expect(screen.getByLabelText("Cantidad de Arroz extra").value).toBe("1");
    expect(screen.getByRole("alert").textContent).toContain("Ahora solo quedan 1 unid. de Arroz extra");
  });

  test("conserva el pedido si no se pudo enviar", () => {
    const onPlaceOrder = vi.fn(() => ({ ok: false, error: "Solo quedan 1 unid. de Leche Gloria." }));
    cart({ onPlaceOrder });
    add("Leche Gloria");
    fireEvent.click(screen.getByRole("button", { name: "Enviar pedido" }));
    expect(screen.getByRole("alert").textContent).toContain("Solo quedan 1");
    expect(screen.getByLabelText("Cantidad de Leche Gloria")).toBeTruthy();
  });

  test("muestra el estado de sus pedidos y deja cancelar los pendientes", () => {
    const line = [{ productoId: 1, productoNombre: "Leche Gloria", cantidad: 2, unidad: "unid.", precio: 4.5, subtotal: 9 }];
    const base = { store: "Bodega San Martín", clienteId: "c1", clienteNombre: "Diego Paz", creadoEn: "2026-11-24T15:00:00.000Z", total: 9, lineas: line };
    const orders = [
      { ...base, id: "ped-1", estado: "pendiente" },
      { ...base, id: "ped-2", estado: "aceptado", atendidoPorNombre: "Ana Torres" },
      { ...base, id: "ped-3", estado: "rechazado", motivoRechazo: "Cerramos temprano" },
    ];
    const { onCancelOrder } = cart({ orders });
    const history = screen.getByRole("region", { name: "Tus pedidos" });
    expect(within(history).getByText("Pendiente")).toBeTruthy();
    expect(within(history).getByText(/Aceptado por Ana Torres/)).toBeTruthy();
    expect(within(history).getByText(/Cerramos temprano/)).toBeTruthy();
    const cancels = within(history).getAllByRole("button", { name: "Cancelar pedido" });
    expect(cancels).toHaveLength(1);
    fireEvent.click(cancels[0]);
    expect(onCancelOrder).toHaveBeenCalledWith("ped-1");
  });
});
