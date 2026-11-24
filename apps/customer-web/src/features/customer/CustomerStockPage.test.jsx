// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, test } from "vitest";
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
  expect(screen.queryByRole("button", { name: /Agregar|Editar|Registrar/ })).toBeNull();
});
