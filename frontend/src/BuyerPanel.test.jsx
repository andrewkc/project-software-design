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

beforeEach(() => { vi.restoreAllMocks(); vi.clearAllMocks(); });
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


test("buyer opens checkout with one click and confirmation is automatic", async () => {
  mockData({ id: "c1", name: "Cliente", role: "CUSTOMER" });
  const popup = { opener: window, location: { replace: vi.fn() }, close: vi.fn() };
  vi.spyOn(window, "open").mockReturnValue(popup);
  apiPost.mockImplementation(async (path) => {
    if (path === "/orders") return { ...order, payment_mode: "MERCADOPAGO_TEST", payment_started: false };
    if (path.endsWith("/checkout")) return { checkout_url: "https://www.mercadopago.com.pe/checkout/test" };
    if (path.endsWith("/verify-payment")) return { ...order, state: "PAID", payment_mode: "MERCADOPAGO_TEST", payment_started: true };
    throw new Error(path);
  });
  render(<BuyerPanel onExit={() => {}} />);
  await screen.findByText("Almendras");
  fireEvent.click(screen.getByText("Añadir"));
  fireEvent.click(screen.getByText("Crear pedido y reservar"));
  fireEvent.click(await screen.findByText("Pagar con Mercado Pago"));
  await waitFor(() => expect(popup.location.replace).toHaveBeenCalledWith("https://www.mercadopago.com.pe/checkout/test"));
  expect(popup.opener).toBeNull();
  await waitFor(() => expect(apiPost).toHaveBeenCalledWith("/orders/order-1234/verify-payment", {}));
  expect(await screen.findByText(/Pago de prueba confirmado/)).toBeTruthy();
  expect(screen.queryByText("Pagar con Mercado Pago")).toBeNull();
});

test("blocked popup leaves a usable checkout link", async () => {
  mockData({ id: "c1", name: "Cliente", role: "CUSTOMER" });
  vi.spyOn(window, "open").mockReturnValue(null);
  apiPost.mockImplementation(async (path) => {
    if (path === "/orders") return { ...order, payment_mode: "MERCADOPAGO_TEST", payment_started: false };
    if (path.endsWith("/checkout")) return { checkout_url: "https://www.mercadopago.com.pe/checkout/test" };
    if (path.endsWith("/verify-payment")) return { ...order, payment_mode: "MERCADOPAGO_TEST", payment_started: true };
    throw new Error(path);
  });
  render(<BuyerPanel onExit={() => {}} />);
  await screen.findByText("Almendras");
  fireEvent.click(screen.getByText("Añadir"));
  fireEvent.click(screen.getByText("Crear pedido y reservar"));
  fireEvent.click(await screen.findByText("Pagar con Mercado Pago"));
  const link = await screen.findByText("Abrir pago de prueba");
  expect(link.getAttribute("href")).toBe("https://www.mercadopago.com.pe/checkout/test");
  expect(link.getAttribute("target")).toBe("_blank");
});

test("pending checkout resumes and verifies after reload", async () => {
  mockData({ id: "c1", name: "Cliente", role: "CUSTOMER" });
  apiGet.mockImplementation(async (path) => {
    if (path === "/stores") return [{ id: "s1", name: "Bodega A", address: "Calle A" }];
    if (path === "/offers") return [offer];
    if (path === "/auth/me") return { id: "c1", name: "Cliente", role: "CUSTOMER" };
    if (path === "/orders") return [{ ...order, payment_mode: "MERCADOPAGO_TEST", payment_started: true }];
    throw new Error(path);
  });
  apiPost.mockResolvedValue({ ...order, state: "PAID", payment_mode: "MERCADOPAGO_TEST", payment_started: true });
  render(<BuyerPanel onExit={() => {}} />);
  await waitFor(() => expect(apiPost).toHaveBeenCalledWith("/orders/order-1234/verify-payment", {}));
  expect(await screen.findByText(/Pago de prueba confirmado/)).toBeTruthy();
});

test("empty basket cannot create an order", async () => {
  mockData({ id: "c1", name: "Cliente", role: "CUSTOMER" });
  render(<BuyerPanel onExit={() => {}} />);
  await screen.findByText("Almendras");
  const button = screen.getByText("Crear pedido y reservar");
  expect(button.disabled).toBe(true);
  fireEvent.click(button);
  expect(apiPost).not.toHaveBeenCalledWith("/orders", expect.anything());
});

test("simultaneous focus events do not duplicate verification", async () => {
  mockData({ id: "c1", name: "Cliente", role: "CUSTOMER" });
  apiGet.mockImplementation(async (path) => {
    if (path === "/stores") return [{ id: "s1", name: "Bodega A", address: "Calle A" }];
    if (path === "/offers") return [offer];
    if (path === "/auth/me") return { id: "c1", name: "Cliente", role: "CUSTOMER" };
    if (path === "/orders") return [{ ...order, payment_mode: "MERCADOPAGO_TEST", payment_started: true }];
    throw new Error(path);
  });
  apiPost.mockImplementation(() => new Promise(() => {}));
  render(<BuyerPanel onExit={() => {}} />);
  await waitFor(() => expect(apiPost).toHaveBeenCalledTimes(1));
  fireEvent.focus(window);
  fireEvent.focus(window);
  expect(apiPost).toHaveBeenCalledTimes(1);
});
