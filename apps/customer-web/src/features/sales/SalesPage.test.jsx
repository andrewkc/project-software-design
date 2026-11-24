// @vitest-environment jsdom
import React from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { SalesPage } from "./SalesPage";
import { LayoutContext } from "../../components/layout/LayoutContext";
import { localToday } from "../../lib/sales";

const future = "2099-01-01";
const products = [
  { id: 1, name: "Leche Gloria", category: "Lácteos", icon: "🥛", stock: 8, unit: "unid.", price: 4.5, expires: future, activo: true },
  { id: 2, name: "Leche chocolatada", category: "Lácteos", icon: "🥛", stock: 8, unit: "unid.", price: 4.8, expires: future, activo: true },
  { id: 3, name: "Arroz extra", category: "Abarrotes", icon: "🍚", stock: 2, unit: "unid.", price: 4.2, expires: "", activo: true },
  { id: 4, name: "Yogurt vencido", category: "Lácteos", icon: "🥛", stock: 5, unit: "unid.", price: 3.8, expires: "2020-01-01", activo: true },
];
const user = { id: "emp-1", role: "empleado", name: "Ana Torres" };
const sale = (id, responsable, nombre) => ({ id, fechaHora: `${localToday()}T15:00:00.000Z`, tipo: "salida", motivo: "Venta", total: 9, responsable, responsableNombre: nombre, detalles: [{ productoId: 1, productoNombre: "Leche Gloria", cantidad: 2, unidad: "unid.", subtotal: 9 }] });

function renderPage(props = {}) {
  const onRegisterSale = vi.fn(() => ({ ok: true }));
  render(<LayoutContext.Provider value={{ user: props.user || user, activeTab: "sales", onNavigate: () => {} }}><SalesPage products={products} movements={[]} user={user} onRegisterSale={onRegisterSale} {...props} /></LayoutContext.Provider>);
  return { onRegisterSale };
}

beforeEach(() => { delete window.SpeechRecognition; delete window.webkitSpeechRecognition; });
afterEach(cleanup);

test("arma la cesta, calcula el total y registra la venta", () => {
  const { onRegisterSale } = renderPage();
  fireEvent.click(screen.getByRole("button", { name: "Agregar Leche Gloria" }));
  fireEvent.click(screen.getByRole("button", { name: "Agregar Leche Gloria" }));
  fireEvent.click(screen.getByRole("button", { name: "Agregar Arroz extra" }));
  expect(screen.getByTestId("sale-total").textContent).toContain("13.20");
  fireEvent.click(screen.getByRole("button", { name: "Registrar venta" }));
  expect(onRegisterSale).toHaveBeenCalledWith([{ productId: 1, quantity: 2 }, { productId: 3, quantity: 1 }]);
  expect(screen.getByText("La cesta está vacía")).toBeTruthy();
});

test("no permite agregar un producto vencido", () => {
  renderPage();
  const button = screen.getByRole("button", { name: "Yogurt vencido no disponible: Vencido" });
  expect(button.disabled).toBe(true);
});

test("no deja superar el stock disponible", () => {
  renderPage();
  const add = screen.getByRole("button", { name: "Agregar Arroz extra" });
  fireEvent.click(add); fireEvent.click(add); fireEvent.click(add);
  expect(screen.getByLabelText("Cantidad de Arroz extra").value).toBe("2");
  expect(screen.getByRole("alert").textContent).toContain("Solo hay 2");
});

test("conserva la cesta y muestra el error si la venta falla", () => {
  const onRegisterSale = vi.fn(() => ({ ok: false, error: "Stock insuficiente para Leche Gloria." }));
  renderPage({ onRegisterSale });
  fireEvent.click(screen.getByRole("button", { name: "Agregar Leche Gloria" }));
  fireEvent.click(screen.getByRole("button", { name: "Registrar venta" }));
  expect(screen.getByRole("alert").textContent).toContain("Stock insuficiente");
  expect(screen.getByLabelText("Cantidad de Leche Gloria")).toBeTruthy();
});

test("el dictado llena la cesta pero nunca registra la venta solo", () => {
  const { onRegisterSale } = renderPage();
  fireEvent.click(screen.getByRole("button", { name: /Dictar venta/ }));
  fireEvent.change(screen.getByLabelText("Texto para interpretar"), { target: { value: "vende dos arroz" } });
  fireEvent.click(screen.getByRole("button", { name: "Interpretar" }));
  expect(screen.getByLabelText("Cantidad de Arroz extra").value).toBe("2");
  expect(onRegisterSale).not.toHaveBeenCalled();
});

test("si el dictado es ambiguo pide elegir el producto", () => {
  renderPage();
  fireEvent.click(screen.getByRole("button", { name: /Dictar venta/ }));
  fireEvent.change(screen.getByLabelText("Texto para interpretar"), { target: { value: "dos leches" } });
  fireEvent.click(screen.getByRole("button", { name: "Interpretar" }));
  expect(screen.queryByLabelText("Cantidad de Leche Gloria")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Elegir Leche chocolatada" }));
  expect(screen.getByLabelText("Cantidad de Leche chocolatada").value).toBe("2");
});

describe("pedidos de clientes", () => {
  const pending = [{ id: "ped-1", store: "Bodega San Martín", clienteId: "cli-1", clienteNombre: "Diego Paz", creadoEn: "2026-11-24T15:00:00.000Z", estado: "pendiente", total: 9, lineas: [{ productoId: 1, productoNombre: "Leche Gloria", cantidad: 2, unidad: "unid.", precio: 4.5, subtotal: 9 }] }];

  test("sin pedidos pendientes no aparece la sección", () => {
    renderPage({ pendingOrders: [] });
    expect(screen.queryByRole("region", { name: "Pedidos de clientes" })).toBeNull();
  });

  test("muestra el pedido y lo acepta como venta", () => {
    const onAcceptOrder = vi.fn(() => ({ ok: true }));
    renderPage({ pendingOrders: pending, onAcceptOrder, onRejectOrder: vi.fn() });
    const inbox = screen.getByRole("region", { name: "Pedidos de clientes" });
    expect(within(inbox).getByText("Diego Paz")).toBeTruthy();
    expect(within(inbox).getByText("2 Leche Gloria")).toBeTruthy();
    expect(within(inbox).getByText("S/ 9.00")).toBeTruthy();
    fireEvent.click(within(inbox).getByRole("button", { name: "Aceptar pedido de Diego Paz" }));
    expect(onAcceptOrder).toHaveBeenCalledWith("ped-1");
  });

  test("si no se puede aceptar muestra el motivo", () => {
    const onAcceptOrder = vi.fn(() => ({ ok: false, error: "Stock insuficiente para Leche Gloria." }));
    renderPage({ pendingOrders: pending, onAcceptOrder, onRejectOrder: vi.fn() });
    fireEvent.click(screen.getByRole("button", { name: "Aceptar pedido de Diego Paz" }));
    expect(within(screen.getByRole("region", { name: "Pedidos de clientes" })).getByRole("alert").textContent).toContain("Stock insuficiente");
  });

  test("rechazar pide un motivo antes de confirmar", () => {
    const onRejectOrder = vi.fn(() => ({ ok: true }));
    renderPage({ pendingOrders: pending, onAcceptOrder: vi.fn(), onRejectOrder });
    fireEvent.click(screen.getByRole("button", { name: "Rechazar pedido de Diego Paz" }));
    fireEvent.change(screen.getByLabelText("Motivo del rechazo"), { target: { value: "Sin stock de leche" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar rechazo" }));
    expect(onRejectOrder).toHaveBeenCalledWith("ped-1", "Sin stock de leche");
  });
});

test("el empleado solo ve sus ventas y el jefe ve todas", () => {
  const movements = [sale("m1", "emp-1", "Ana Torres"), sale("m2", "emp-2", "Luis Paz")];
  renderPage({ movements });
  const history = screen.getByRole("region", { name: "Ventas recientes" });
  expect(within(history).getByText(/Ana Torres/)).toBeTruthy();
  expect(within(history).queryByText(/Luis Paz/)).toBeNull();
  cleanup();
  const jefe = { id: "user-jefe", role: "jefe", name: "Kelvin" };
  renderPage({ user: jefe, movements });
  expect(within(screen.getByRole("region", { name: "Ventas recientes" })).getByText(/Luis Paz/)).toBeTruthy();
});
