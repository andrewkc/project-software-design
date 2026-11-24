import { describe, expect, test } from "vitest";
import { applyQuery, buildProfile, deleteBlockReason, validateProfile } from "./adminProfiles";
import { isAdmin, isCliente, isJefe, withUserDefaults } from "./permissions";

const rows = [
  { id: "jefe-1", role: "jefe", name: "Kelvin Ruiz", email: "kelvin@correo.pe", store: "Bodega San Martín", activo: true, creadoEn: "2026-10-01T10:00:00.000Z" },
  { id: "jefe-2", role: "jefe", name: "Álvaro Núñez", email: "alvaro@correo.pe", store: "Bodega Lima", activo: false, creadoEn: "2026-11-02T10:00:00.000Z" },
  { id: "emp-1", role: "empleado", name: "Ana Torres", email: "ana@correo.pe", store: "Bodega San Martín", activo: true, creadoEn: "2026-10-05T10:00:00.000Z" },
  { id: "cli-1", role: "cliente", name: "Diego Paz", email: "diego@correo.pe", store: "Bodega Lima", activo: true, creadoEn: "" },
  { id: "adm-1", role: "admin", name: "Walter Admin", email: "admin@bodesmart.pe", store: "", activo: true, creadoEn: "2026-09-01T10:00:00.000Z" },
];
const ids = (list) => list.map((row) => row.id);

describe("applyQuery", () => {
  test("filtra por rol de la vista", () => {
    expect(ids(applyQuery(rows, { role: "jefe" }))).toEqual(["jefe-1", "jefe-2"]);
  });

  test("busca sin tildes por nombre, correo o bodega", () => {
    expect(ids(applyQuery(rows, { search: "alvaro" }))).toEqual(["jefe-2"]);
    expect(ids(applyQuery(rows, { search: "lima" }))).toEqual(["jefe-2", "cli-1"]);
  });

  test("combina filtros con Y e ignora los incompletos", () => {
    const filters = [
      { field: "store", operator: "contains", value: "san martín" },
      { field: "activo", operator: "is", value: "true" },
      { field: "email", operator: "contains", value: "" },
    ];
    expect(ids(applyQuery(rows, { filters }))).toEqual(["jefe-1", "emp-1"]);
    expect(ids(applyQuery(rows, { filters: [{ field: "creadoEn", operator: "after", value: "2026-10-04" }] }))).toEqual(["jefe-2", "emp-1"]);
    expect(ids(applyQuery(rows, { filters: [{ field: "creadoEn", operator: "is_empty" }] }))).toEqual(["cli-1"]);
  });

  test("ordena por varias columnas y deja los vacíos al final", () => {
    expect(ids(applyQuery(rows, { sorts: [{ field: "role", direction: "asc" }, { field: "name", direction: "desc" }] }))).toEqual(["adm-1", "cli-1", "emp-1", "jefe-1", "jefe-2"]);
    expect(ids(applyQuery(rows, { sorts: [{ field: "creadoEn", direction: "desc" }] })).at(-1)).toBe("cli-1");
  });
});

describe("validateProfile", () => {
  const draft = { nombres: "Lucía", apellidos: "Vega", email: "lucia@correo.pe", role: "empleado", store: "Bodega Lima", password: "segura123", activo: true };

  test("acepta un perfil nuevo completo", () => {
    expect(validateProfile(draft, rows)).toBeNull();
  });

  test("exige nombre, correo válido y bodega para roles de bodega", () => {
    expect(validateProfile({ ...draft, nombres: " " }, rows)).toBe("Ingresa los nombres.");
    expect(validateProfile({ ...draft, email: "lucia" }, rows)).toBe("Ingresa un correo válido.");
    expect(validateProfile({ ...draft, store: "" }, rows)).toBe("Indica la bodega.");
    expect(validateProfile({ ...draft, role: "admin", store: "" }, rows)).toBeNull();
  });

  test("el correo no se puede repetir, sin importar mayúsculas", () => {
    expect(validateProfile({ ...draft, email: "ANA@correo.pe" }, rows)).toBe("Ya existe una cuenta con ese correo.");
    expect(validateProfile({ ...draft, email: "ana@correo.pe", password: "" }, rows, { editingId: "emp-1" })).toBeNull();
  });

  test("la contraseña es obligatoria al crear y opcional al editar", () => {
    expect(validateProfile({ ...draft, password: "" }, rows)).toBe("La contraseña debe tener al menos 8 caracteres.");
    expect(validateProfile({ ...draft, password: "corta" }, rows, { editingId: "emp-1", ...{} })).toBe("La contraseña debe tener al menos 8 caracteres.");
  });

  test("una bodega solo tiene un jefe activo", () => {
    expect(validateProfile({ ...draft, role: "jefe", store: "bodega san martin" }, rows)).toBe("Esa bodega ya tiene un jefe activo.");
    expect(validateProfile({ ...draft, role: "jefe", store: "Bodega Lima" }, rows)).toBeNull();
  });

  test("el administrador no puede quitarse el rol ni desactivarse", () => {
    const self = { ...rows[4], nombres: "Walter", apellidos: "Admin", password: "" };
    expect(validateProfile({ ...self, role: "jefe", store: "Bodega Lima" }, rows, { editingId: "adm-1", selfId: "adm-1" })).toBe("No puedes cambiar tu propio rol.");
    expect(validateProfile({ ...self, activo: false }, rows, { editingId: "adm-1", selfId: "adm-1" })).toBe("No puedes desactivar tu propia cuenta.");
  });
});

describe("buildProfile", () => {
  test("crea la cuenta con id por rol, correo normalizado y nombre completo", () => {
    const profile = buildProfile({ nombres: " Lucía ", apellidos: "Vega", email: " Lucia@Correo.pe ", role: "cliente", store: "Bodega Lima", password: "segura123", activo: true }, null, { now: "2026-11-24T10:00:00.000Z", stamp: 7 });
    expect(profile).toEqual({ id: "cli-7", role: "cliente", nombres: "Lucía", apellidos: "Vega", name: "Lucía Vega", email: "lucia@correo.pe", store: "Bodega Lima", password: "segura123", activo: true, creadoEn: "2026-11-24T10:00:00.000Z" });
  });

  test("al editar conserva id, fecha y contraseña si no se cambia; el admin no tiene bodega", () => {
    const existing = { id: "emp-1", role: "empleado", password: "vieja1234", creadoEn: "2026-10-05T10:00:00.000Z", revocadoEn: "" };
    const profile = buildProfile({ nombres: "Ana", apellidos: "Torres", email: "ana@correo.pe", role: "admin", store: "Bodega Lima", password: "", activo: false }, existing, { now: "2026-11-24T10:00:00.000Z" });
    expect(profile).toMatchObject({ id: "emp-1", role: "admin", store: "", password: "vieja1234", activo: false, creadoEn: "2026-10-05T10:00:00.000Z", revocadoEn: "2026-11-24T10:00:00.000Z" });
  });
});

describe("deleteBlockReason", () => {
  const history = { products: [{ id: 1, creadoPor: "emp-1" }], movements: [{ responsable: "jefe-1" }], orders: [{ clienteId: "cli-1" }] };

  test("no se elimina a uno mismo ni a quien tiene historial", () => {
    expect(deleteBlockReason(rows[4], history, "adm-1")).toBe("No puedes eliminar tu propia cuenta.");
    expect(deleteBlockReason(rows[2], history, "adm-1")).toMatch(/historial/);
    expect(deleteBlockReason(rows[0], history, "adm-1")).toMatch(/historial/);
    expect(deleteBlockReason(rows[3], history, "adm-1")).toMatch(/historial/);
    expect(deleteBlockReason(rows[1], history, "adm-1")).toBeNull();
  });
});

describe("rol administrador", () => {
  test("se reconoce y no hereda permisos de jefe ni de cliente", () => {
    const admin = withUserDefaults({ id: "adm-1", role: "admin", name: "Walter" });
    expect(admin.role).toBe("admin");
    expect(admin.store).toBe("");
    expect(isAdmin(admin)).toBe(true);
    expect(isJefe(admin)).toBe(false);
    expect(isCliente(admin)).toBe(false);
  });
});
