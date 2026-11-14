// @vitest-environment jsdom
import React from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import AdminPanel from "./AdminPanel";
import { apiDelete, apiGet, apiPatch, apiPost } from "./api";

vi.mock("./api", () => ({ apiGet: vi.fn(), apiPost: vi.fn(), apiPatch: vi.fn(), apiDelete: vi.fn() }));

const admin = { id: "a1", name: "Admin demo", email: "admin@demo.example", role: "ADMIN", store_id: null };
const stores = [{ id: "s1", name: "Mercado Verde", active: true }, { id: "s2", name: "Dulce y Fresco", active: true }];
const users = [
  { id: "a1", name: "Admin demo", email: "admin@demo.example", role: "ADMIN", store_id: null, store_name: null, is_active: true, last_login: "2026-11-13T10:00:00Z", created_at: "2026-09-01T10:00:00Z" },
  { id: "o1", name: "Carla Ruiz", email: "carla@demo.example", role: "OWNER", store_id: "s2", store_name: "Dulce y Fresco", is_active: true, last_login: null, created_at: "2026-09-02T10:00:00Z" },
  { id: "o2", name: "Ana Torres", email: "ana@demo.example", role: "OWNER", store_id: "s1", store_name: "Mercado Verde", is_active: false, last_login: null, created_at: "2026-09-03T10:00:00Z" },
  { id: "e1", name: "Bruno Díaz", email: "bruno@demo.example", role: "EMPLOYEE", store_id: "s1", store_name: "Mercado Verde", is_active: true, last_login: null, created_at: "2026-09-04T10:00:00Z" },
  { id: "c1", name: "Diego Paz", email: "diego@demo.example", role: "CUSTOMER", store_id: null, store_name: null, is_active: true, last_login: null, created_at: "2026-09-05T10:00:00Z" },
];

function mockSession(user = admin) {
  apiGet.mockImplementation(async (path) => {
    if (path === "/auth/me") return user;
    if (path === "/admin/users") return users;
    if (path === "/admin/stores") return stores;
    throw new Error(`Unexpected ${path}`);
  });
  apiPost.mockResolvedValue({ id: "new" });
  apiPatch.mockResolvedValue({ id: "saved" });
  apiDelete.mockResolvedValue(null);
}

const bodyNames = () => screen.getAllByRole("row").slice(1).map((row) => within(row).getAllByRole("cell")[0].textContent);

async function renderAdmin(user) {
  mockSession(user);
  render(<AdminPanel onExit={() => {}} />);
  if (!user || user.role === "ADMIN") await screen.findByRole("table");
}

beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

test("asks for login when there is no session", async () => {
  apiGet.mockRejectedValue(new Error("not logged in"));
  render(<AdminPanel onExit={() => {}} />);
  expect(await screen.findByText("Ingresar como administrador")).toBeTruthy();
  expect(screen.queryByRole("table")).toBeNull();
});

test("non-admin accounts do not see the profiles table", async () => {
  await renderAdmin({ ...admin, role: "OWNER", store_id: "s1" });
  expect(await screen.findByText(/solo para administradores/i)).toBeTruthy();
  expect(screen.queryByRole("table")).toBeNull();
  expect(apiGet).not.toHaveBeenCalledWith("/admin/users");
});

test("main view lists only the warehouse owners", async () => {
  await renderAdmin();
  expect(screen.getByRole("tab", { name: /Jefes de bodega/ }).getAttribute("aria-selected")).toBe("true");
  expect(bodyNames().sort()).toEqual(["Ana Torres", "Carla Ruiz"]);
});

test("tabs switch to other profile types with counts", async () => {
  await renderAdmin();
  fireEvent.click(screen.getByRole("tab", { name: /Todos.*5/ }));
  expect(bodyNames()).toHaveLength(5);
  fireEvent.click(screen.getByRole("tab", { name: /Clientes.*1/ }));
  expect(bodyNames()).toEqual(["Diego Paz"]);
});

test("search narrows the rows", async () => {
  await renderAdmin();
  fireEvent.change(screen.getByLabelText("Buscar perfiles"), { target: { value: "verde" } });
  expect(bodyNames()).toEqual(["Ana Torres"]);
});

test("clicking a column header sorts ascending then descending", async () => {
  await renderAdmin();
  fireEvent.click(screen.getByRole("button", { name: /^Nombre/ }));
  expect(bodyNames()).toEqual(["Ana Torres", "Carla Ruiz"]);
  fireEvent.click(screen.getByRole("button", { name: /^Nombre/ }));
  expect(bodyNames()).toEqual(["Carla Ruiz", "Ana Torres"]);
});

test("filter builder narrows by any field", async () => {
  await renderAdmin();
  fireEvent.click(screen.getByRole("button", { name: /Filtro/ }));
  fireEvent.change(screen.getByLabelText("Campo del filtro 1"), { target: { value: "is_active" } });
  fireEvent.change(screen.getByLabelText("Valor del filtro 1"), { target: { value: "false" } });
  expect(bodyNames()).toEqual(["Ana Torres"]);
  fireEvent.click(screen.getByRole("button", { name: "Quitar filtro 1" }));
  expect(bodyNames()).toHaveLength(2);
});

test("sort builder orders by any field", async () => {
  await renderAdmin();
  fireEvent.click(screen.getByRole("tab", { name: /Todos/ }));
  fireEvent.click(screen.getByRole("button", { name: /Ordenar/ }));
  fireEvent.change(screen.getByLabelText("Campo del orden 1"), { target: { value: "created_at" } });
  fireEvent.change(screen.getByLabelText("Dirección del orden 1"), { target: { value: "desc" } });
  expect(bodyNames()[0]).toBe("Diego Paz");
});

test("creates an owner for a store", async () => {
  await renderAdmin();
  fireEvent.click(screen.getByRole("button", { name: /Nuevo perfil/ }));
  const dialog = screen.getByRole("dialog", { name: "Nuevo perfil" });
  fireEvent.change(within(dialog).getByLabelText("Nombre"), { target: { value: "Eva Luna" } });
  fireEvent.change(within(dialog).getByLabelText("Correo"), { target: { value: "eva@demo.example" } });
  fireEvent.change(within(dialog).getByLabelText("Bodega"), { target: { value: "s2" } });
  fireEvent.change(within(dialog).getByLabelText("Contraseña"), { target: { value: "ClaveSegura2026!" } });
  fireEvent.click(within(dialog).getByRole("button", { name: "Crear perfil" }));
  await waitFor(() => expect(apiPost).toHaveBeenCalledWith("/admin/users", {
    name: "Eva Luna", email: "eva@demo.example", role: "OWNER", store_id: "s2", password: "ClaveSegura2026!",
  }));
  expect(await screen.findByText("Perfil creado.")).toBeTruthy();
});

test("store field disappears for customers", async () => {
  await renderAdmin();
  fireEvent.click(screen.getByRole("button", { name: /Nuevo perfil/ }));
  const dialog = screen.getByRole("dialog", { name: "Nuevo perfil" });
  fireEvent.change(within(dialog).getByLabelText("Rol"), { target: { value: "CUSTOMER" } });
  expect(within(dialog).queryByLabelText("Bodega")).toBeNull();
});

test("edits a profile without sending an empty password", async () => {
  await renderAdmin();
  fireEvent.click(screen.getByRole("button", { name: "Carla Ruiz" }));
  const dialog = screen.getByRole("dialog", { name: "Editar perfil" });
  fireEvent.change(within(dialog).getByLabelText("Nombre"), { target: { value: "Carla Ruiz Soto" } });
  fireEvent.click(within(dialog).getByRole("button", { name: "Guardar cambios" }));
  await waitFor(() => expect(apiPatch).toHaveBeenCalledWith("/admin/users/o1", {
    name: "Carla Ruiz Soto", email: "carla@demo.example", role: "OWNER", store_id: "s2", is_active: true,
  }));
});

test("deletes a profile after confirming", async () => {
  await renderAdmin();
  fireEvent.click(screen.getByRole("button", { name: "Carla Ruiz" }));
  const dialog = screen.getByRole("dialog", { name: "Editar perfil" });
  fireEvent.click(within(dialog).getByRole("button", { name: "Eliminar" }));
  expect(apiDelete).not.toHaveBeenCalled();
  fireEvent.click(within(dialog).getByRole("button", { name: "Sí, eliminar" }));
  await waitFor(() => expect(apiDelete).toHaveBeenCalledWith("/admin/users/o1"));
  expect(await screen.findByText("Perfil eliminado.")).toBeTruthy();
});

test("profiles with history offer deactivation instead", async () => {
  await renderAdmin();
  apiDelete.mockRejectedValue(Object.assign(new Error("La cuenta tiene historial"), { code: "HAS_HISTORY", status: 409 }));
  fireEvent.click(screen.getByRole("button", { name: "Carla Ruiz" }));
  const dialog = screen.getByRole("dialog", { name: "Editar perfil" });
  fireEvent.click(within(dialog).getByRole("button", { name: "Eliminar" }));
  fireEvent.click(within(dialog).getByRole("button", { name: "Sí, eliminar" }));
  fireEvent.click(await within(dialog).findByRole("button", { name: "Desactivar en su lugar" }));
  await waitFor(() => expect(apiPatch).toHaveBeenCalledWith("/admin/users/o1", { is_active: false }));
});

test("the signed-in admin cannot delete their own profile", async () => {
  await renderAdmin();
  fireEvent.click(screen.getByRole("tab", { name: /Administradores/ }));
  fireEvent.click(screen.getByRole("button", { name: "Admin demo" }));
  const dialog = screen.getByRole("dialog", { name: "Editar perfil" });
  expect(within(dialog).queryByRole("button", { name: "Eliminar" })).toBeNull();
});
