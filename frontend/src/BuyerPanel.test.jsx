// @vitest-environment jsdom
import React from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import BuyerPanel from "./BuyerPanel";
import { apiGet, apiPost } from "./api";

vi.mock("./api", () => ({ apiGet: vi.fn(), apiPost: vi.fn() }));

const offer = { id: "o1", store_id: "s1", product_name: "Almendras", category: "Frutos secos",
  expiry_date: "2026-11-10", storage_conditions: "Seco", sale_step: 250, unit: "G",
  available_steps: 4, current_price: "9.00" };
const order = { id: "order-1234", state: "PENDING", total: "18.00", pickup_address: "Calle A",
  reservation_until: "2026-11-01T12:00:00Z" };

function mockData(user = null) {
  apiGet.mockImplementation(async (path) => {
    if (path === "/stores") return [{ id: "s1", name: "Bodega A", address: "Calle A" }, { id: "s2", name: "Bodega B", address: "Calle B" }];
    if (path === "/offers") return [offer, { ...offer, id: "o2", store_id: "s2", product_name: "Pasas" }];
    if (path === "/auth/me") {
      if (!user) throw new Error("No session");
      return user;
    }
    if (path === "/orders") return [];
    throw new Error(`Unexpected ${path}`);
  });
  apiPost.mockResolvedValue(order);
}

beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

test("public catalog only shows the selected store and changing store clears basket", async () => {
  mockData();
  render(<BuyerPanel onExit={() => {}} />);
  expect(await screen.findByText("Almendras")).toBeTruthy();
  expect(screen.queryByText("Pasas")).toBeNull();
  fireEvent.click(screen.getByText("Añadir"));
  expect(screen.getByText("250 G · S/ 9.00")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Bodega"), { target: { value: "s2" } });
  expect(await screen.findByText("Pasas")).toBeTruthy();
  expect(screen.getByText("Agrega productos de una sola bodega.")).toBeTruthy();
});

test("buyer sends quantities in base units and can simulate approval", async () => {
  mockData({ id: "c1", name: "Cliente", role: "CUSTOMER" });
  render(<BuyerPanel onExit={() => {}} />);
  await screen.findByText("Almendras");
  fireEvent.click(screen.getByText("Añadir"));
  fireEvent.click(screen.getByText("Añadir"));
  fireEvent.click(screen.getByText("Crear pedido y reservar"));
  await waitFor(() => expect(apiPost).toHaveBeenCalledWith("/orders", expect.objectContaining({
    idempotency_key: expect.any(String), lines: [{ offer_id: "o1", base_quantity: 500 }],
  })));
  fireEvent.click(await screen.findByText("Simular pago aprobado"));
  await waitFor(() => expect(apiPost).toHaveBeenCalledWith("/orders/order-1234/simulate-payment", { decision: "APPROVE" }));
});

test("buyer can ask the local read-only assistant", async () => {
  mockData();
  apiPost.mockResolvedValue({ answer: "Almendras disponibles", mode: "LOCAL_DEMO" });
  render(<BuyerPanel onExit={() => {}} />);
  const input = await screen.findByPlaceholderText("¿Qué ofertas hay?");
  fireEvent.change(input, { target: { value: "¿Qué ofertas hay?" } });
  fireEvent.submit(input.closest("form"));
  await waitFor(() => expect(apiPost).toHaveBeenCalledWith("/chat", { question: "¿Qué ofertas hay?" }));
  expect(await screen.findByText("Almendras disponibles")).toBeTruthy();
});
