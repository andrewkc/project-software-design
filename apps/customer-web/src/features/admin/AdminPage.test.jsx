// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, test, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { AdminPage } from "./AdminPage";
import { LayoutContext } from "../../components/layout/LayoutContext";

const admin = { id: "adm-1", role: "admin", name: "Walter Admin", nombres: "Walter", apellidos: "Admin", email: "admin@bodesmart.pe", store: "", activo: true, creadoEn: "2026-09-01T10:00:00.000Z" };
const profiles = [
  { id: "jefe-1", role: "jefe", name: "Kelvin Ruiz", nombres: "Kelvin", apellidos: "Ruiz", email: "kelvin@correo.pe", store: "Bodega San Martín", password: "clave1234", activo: true, creadoEn: "2026-10-01T10:00:00.000Z" },
  { id: "jefe-2", role: "jefe", name: "Álvaro Núñez", nombres: "Álvaro", apellidos: "Núñez", email: "alvaro@correo.pe", store: "Bodega Lima", activo: false, creadoEn: "2026-11-02T10:00:00.000Z" },
  { id: "emp-1", role: "empleado", name: "Ana Torres", nombres: "Ana", apellidos: "Torres", email: "ana@correo.pe", store: "Bodega San Martín", activo: true, creadoEn: "2026-10-05T10:00:00.000Z" },
  { id: "cli-1", role: "cliente", name: "Diego Paz", nombres: "Diego", apellidos: "Paz", email: "diego@correo.pe", store: "Bodega Lima", activo: true, creadoEn: "2026-11-10T10:00:00.000Z" },
  admin,
];
const history = { products: [], movements: [{ responsable: "jefe-1" }], orders: [] };

function renderPage() {
  const onSave = vi.fn();
  const onDelete = vi.fn();
  render(<LayoutContext.Provider value={{ user: admin, activeTab: "admin", onNavigate: () => {} }}><AdminPage user={admin} profiles={profiles} history={history} onSave={onSave} onDelete={onDelete} /></LayoutContext.Provider>);
  return { onSave, onDelete };
}
const names = () => within(screen.getByRole("table")).getAllByRole("row").slice(1).map((row) => row.cells[0].textContent);
const open = (name) => fireEvent.click(screen.getByRole("button", { name }));
const fill = (label, value) => fireEvent.change(within(screen.getByRole("dialog")).getByLabelText(label), { target: { value } });

afterEach(cleanup);

test("la vista principal lista a los jefes de bodega", () => {
  renderPage();
  expect(screen.getByRole("tab", { name: /Jefes de bodega/ }).getAttribute("aria-selected")).toBe("true");
  expect(screen.getByRole("tab", { name: /Jefes de bodega/ }).textContent).toContain("2");
  expect(names()).toEqual(["Kelvin Ruiz", "Álvaro Núñez"]);
  fireEvent.click(screen.getByRole("tab", { name: /Clientes/ }));
  expect(names()).toEqual(["Diego Paz"]);
  fireEvent.click(screen.getByRole("tab", { name: /Todos/ }));
  expect(names()).toHaveLength(5);
});

test("busca sin tildes y ordena desde la cabecera", () => {
  renderPage();
  fireEvent.change(screen.getByLabelText("Buscar perfiles"), { target: { value: "alvaro" } });
  expect(names()).toEqual(["Álvaro Núñez"]);
  fireEvent.change(screen.getByLabelText("Buscar perfiles"), { target: { value: "" } });
  fireEvent.click(screen.getByRole("button", { name: "Nombre" }));
  expect(names()).toEqual(["Álvaro Núñez", "Kelvin Ruiz"]);
  fireEvent.click(screen.getByRole("button", { name: "Nombre ↑" }));
  expect(names()).toEqual(["Kelvin Ruiz", "Álvaro Núñez"]);
});

test("filtra como en Notion por cualquier campo", () => {
  renderPage();
  fireEvent.click(screen.getByRole("button", { name: "Filtro" }));
  fireEvent.change(screen.getByLabelText("Campo del filtro 1"), { target: { value: "activo" } });
  fireEvent.change(screen.getByLabelText("Valor del filtro 1"), { target: { value: "false" } });
  expect(names()).toEqual(["Álvaro Núñez"]);
  fireEvent.click(screen.getByRole("button", { name: "Quitar filtro 1" }));
  expect(names()).toHaveLength(2);
});

test("crea un perfil y valida el correo repetido", () => {
  const { onSave } = renderPage();
  open("Nuevo perfil");
  fill("Nombres", "Lucía");
  fill("Apellidos", "Vega");
  fill("Correo", "ANA@correo.pe");
  fill("Bodega", "Bodega Lima");
  fill("Contraseña", "segura123");
  fireEvent.click(screen.getByRole("button", { name: "Crear perfil" }));
  expect(within(screen.getByRole("dialog")).getByRole("alert").textContent).toBe("Ya existe una cuenta con ese correo.");
  expect(onSave).not.toHaveBeenCalled();
  fill("Correo", "lucia@correo.pe");
  fireEvent.click(screen.getByRole("button", { name: "Crear perfil" }));
  expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ role: "jefe", name: "Lucía Vega", email: "lucia@correo.pe", store: "Bodega Lima", activo: true }));
});

test("edita un perfil y conserva su contraseña si no se cambia", () => {
  const { onSave } = renderPage();
  open("Kelvin Ruiz");
  expect(within(screen.getByRole("dialog")).getByRole("heading", { name: "Kelvin Ruiz" })).toBeTruthy();
  fill("Bodega", "Bodega Norte");
  fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
  expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ id: "jefe-1", store: "Bodega Norte", password: "clave1234" }));
});

test("no elimina a quien tiene historial y ofrece desactivarlo", () => {
  const { onSave, onDelete } = renderPage();
  open("Kelvin Ruiz");
  fireEvent.click(screen.getByRole("button", { name: "Eliminar perfil" }));
  fireEvent.click(screen.getByRole("button", { name: "Sí, eliminar" }));
  expect(onDelete).not.toHaveBeenCalled();
  expect(within(screen.getByRole("dialog")).getByRole("alert").textContent).toMatch(/historial/);
  fireEvent.click(screen.getByRole("button", { name: "Desactivar en su lugar" }));
  expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ id: "jefe-1", activo: false }));
});

test("elimina un perfil sin historial tras confirmar", () => {
  const { onDelete } = renderPage();
  open("Álvaro Núñez");
  fireEvent.click(screen.getByRole("button", { name: "Eliminar perfil" }));
  fireEvent.click(screen.getByRole("button", { name: "Sí, eliminar" }));
  expect(onDelete).toHaveBeenCalledWith(expect.objectContaining({ id: "jefe-2" }));
});

test("la propia cuenta no se puede degradar, desactivar ni eliminar", () => {
  renderPage();
  fireEvent.click(screen.getByRole("tab", { name: /Administradores/ }));
  open("Walter Admin");
  const dialog = screen.getByRole("dialog");
  expect(within(dialog).getByLabelText("Rol").disabled).toBe(true);
  expect(within(dialog).getByLabelText("Cuenta activa").disabled).toBe(true);
  expect(within(dialog).queryByRole("button", { name: "Eliminar perfil" })).toBeNull();
});

test("el administrador no ve inventario ni ventas de las bodegas", () => {
  renderPage();
  expect(document.body.textContent).not.toMatch(/S\/|stock|venta/i);
});
