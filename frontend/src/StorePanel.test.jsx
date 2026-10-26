// @vitest-environment jsdom
import React from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import StorePanel from "./StorePanel";
import { apiGet, apiPost } from "./api";

vi.mock("./api", () => ({ apiGet: vi.fn(), apiPost: vi.fn() }));

const owner = { id: "o1", name: "Dueño", role: "OWNER", store_id: "s1" };
const employee = { id: "e1", name: "Empleado", role: "EMPLOYEE", store_id: "s1" };
const product = { id: "p1", name: "Almendras", code: "ALM", sale_step: 250, unit: "G", reference_price: "10.00" };
const lot = { id: "l1", product_id: "p1", product_name: "Almendras", code: "ALM-01", expiry_date: "2026-11-10",
  physical_qty: 1250, reserved_qty: 0, available_qty: 1250, total_cost: "25.00" };
const offer = { id: "f1", product_id: "p1", product_name: "Almendras", lot_code: "ALM-01", expiry_date: "2026-11-10",
  state: "PUBLISHED", original_price: "10.00", current_price: "9.00", limit: { max_discount_pct: "30.00", effective_floor: "7.00" } };

function mockSession(user) {
  apiGet.mockImplementation(async (path) => {
    if (path === "/auth/me") return user;
    if (path === "/store/products") return [product];
    if (path === "/store/lots") return [user.role === "OWNER" ? lot : (({ total_cost, ...publicLot }) => publicLot)(lot)];
    if (path === "/store/offers") return [user.role === "OWNER" ? offer : (({ limit, ...publicOffer }) => publicOffer)(offer)];
    if (path === "/store/movements") return [];
    throw new Error(`Unexpected ${path}`);
  });
  apiPost.mockResolvedValue({ id: "saved" });
}

beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

test("asks for login when there is no session", async () => {
  apiGet.mockRejectedValue(new Error("not logged in"));
  render(<StorePanel onExit={() => {}} />);
  expect(await screen.findByText("Ingresar a la bodega")).toBeTruthy();
  expect(screen.queryByText("Venta presencial")).toBeNull();
});

test("owner can see stock, costs and management forms", async () => {
  mockSession(owner);
  render(<StorePanel onExit={() => {}} />);
  expect(await screen.findByText("Ingreso y nuevo lote")).toBeTruthy();
  expect(screen.getByText("Merma")).toBeTruthy();
  expect(screen.getByText("Costo total")).toBeTruthy();
  expect(await screen.findByText("Límite: 30.00% · piso efectivo S/ 7.00")).toBeTruthy();
});

test("employee sees sales but not owner controls or costs", async () => {
  mockSession(employee);
  render(<StorePanel onExit={() => {}} />);
  expect(await screen.findByText("Venta presencial")).toBeTruthy();
  expect(screen.queryByText("Ingreso y nuevo lote")).toBeNull();
  expect(screen.queryByText("Merma")).toBeNull();
  expect(screen.queryByText("Costo total")).toBeNull();
  expect(screen.queryByText(/piso efectivo/)).toBeNull();
});

test("sale form sends server product, quantity and unique retry key", async () => {
  mockSession(employee);
  render(<StorePanel onExit={() => {}} />);
  await screen.findByRole("option", { name: /Almendras · paso 250 G/ });
  const saleForm = screen.getByText("Venta presencial").closest("form");
  fireEvent.change(saleForm.querySelector('input[name="quantity"]'), { target: { value: "500" } });
  fireEvent.submit(saleForm);
  await waitFor(() => expect(apiPost).toHaveBeenCalledWith("/store/local-sales", expect.objectContaining({
    product_id: "p1", quantity: "500", idempotency_key: expect.any(String),
  })));
});

test("owner limit form sends explicit false when below-cost box is unchecked", async () => {
  mockSession(owner);
  render(<StorePanel onExit={() => {}} />);
  await screen.findByText("Ingreso y nuevo lote");
  const limitButton = screen.getByText("Guardar límites");
  const limitForm = limitButton.closest("form");
  fireEvent.change(limitForm.querySelector('input[name="max_discount_pct"]'), { target: { value: "30" } });
  fireEvent.change(limitForm.querySelector('input[name="minimum_price"]'), { target: { value: "7" } });
  fireEvent.submit(limitForm);
  await waitFor(() => expect(apiPost).toHaveBeenCalledWith("/store/offers/f1/limits", expect.objectContaining({
    below_cost_authorized: false, max_discount_pct: "30", minimum_price: "7",
  })));
});
