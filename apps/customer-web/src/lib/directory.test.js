// @vitest-environment jsdom
import { beforeEach, describe, expect, test } from "vitest";
import { DIRECTORY_KEYS, findAccount, mergeProfiles, readDirectory, writeDirectory } from "./directory";

const jefe = { id: "user-jefe", role: "jefe", name: "Kelvin Ruiz", email: "kelvin@correo.pe", store: "Bodega San Martín", activo: true };
const empleado = { id: "emp-1", role: "empleado", name: "Ana Torres", email: "ana@correo.pe", store: "Bodega San Martín", activo: true };
const cliente = { id: "cli-1", role: "cliente", name: "Diego Paz", email: "diego@correo.pe", store: "Bodega San Martín", activo: true };
const admin = { id: "adm-1", role: "admin", name: "Walter Admin", email: "admin@bodesmart.pe", store: "", activo: true };

beforeEach(() => localStorage.clear());

describe("directorio de cuentas en el navegador", () => {
  test("guarda cada rol en su propia clave y las vuelve a leer", () => {
    writeDirectory([jefe, empleado, cliente, admin]);
    expect(JSON.parse(localStorage.getItem(DIRECTORY_KEYS.empleado))).toEqual([empleado]);
    expect(JSON.parse(localStorage.getItem(DIRECTORY_KEYS.cliente))).toEqual([cliente]);
    expect(JSON.parse(localStorage.getItem(DIRECTORY_KEYS.admin))).toEqual([admin]);
    expect(readDirectory().map((item) => item.id).sort()).toEqual(["adm-1", "cli-1", "emp-1", "user-jefe"]);
  });

  test("mantiene la clave antigua del jefe al día", () => {
    writeDirectory([{ ...jefe, name: "Kelvin R." }]);
    expect(JSON.parse(localStorage.getItem("bodega-jefe")).name).toBe("Kelvin R.");
  });

  test("lee el jefe guardado por versiones anteriores", () => {
    localStorage.setItem("bodega-jefe", JSON.stringify(jefe));
    expect(readDirectory()).toEqual([jefe]);
  });

  test("ignora valores corruptos", () => {
    localStorage.setItem(DIRECTORY_KEYS.cliente, "{no es json");
    expect(readDirectory()).toEqual([]);
  });

  test("une con SQLite sin duplicar y gana la copia local", () => {
    const merged = mergeProfiles([{ ...empleado, activo: false }], [empleado, cliente]);
    expect(merged).toHaveLength(2);
    expect(merged.find((item) => item.id === "emp-1").activo).toBe(false);
  });

  test("busca la cuenta por correo sin importar mayúsculas", () => {
    expect(findAccount([jefe, cliente], "DIEGO@correo.pe")).toBe(cliente);
    expect(findAccount([jefe], "nadie@correo.pe")).toBeNull();
  });
});
