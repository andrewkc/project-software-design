import { describe, expect, test } from "vitest";
import { parseLabelText } from "./labelParser";

describe("parseLabelText", () => {
  test("extrae nombre, precio y vencimiento de una etiqueta", () => {
    expect(parseLabelText("LECHE GLORIA ENTERA\n400 g\nS/ 4.50\nVENCE: 20/12/2026")).toMatchObject({
      name: "Leche Gloria Entera", price: 4.5, expires: "2026-12-20", category: "Lácteos",
    });
  });
  test("acepta S/. con coma y fecha con guiones o año corto", () => {
    expect(parseLabelText("ARROZ EXTRA\nS/. 4,20\nFV 05-01-27")).toMatchObject({ price: 4.2, expires: "2027-01-05" });
  });
  test("prefiere la fecha de vencimiento sobre la de fabricación", () => {
    expect(parseLabelText("ATUN\nFAB 01/01/2026\nEXP 01/01/2028").expires).toBe("2028-01-01");
  });
  test("sin palabra clave toma la fecha más lejana", () => {
    expect(parseLabelText("YOGURT\n01/11/2026\n15/12/2026").expires).toBe("2026-12-15");
  });
  test("no usa como nombre líneas de datos ni ruido", () => {
    expect(parseLabelText("@@ ~~\n12345\nINGREDIENTES: sal\nGALLETAS DE SODA\nLOTE 88").name).toBe("Galletas De Soda");
  });
  test("no inventa datos ausentes", () => {
    expect(parseLabelText("### 12")).toEqual({ name: "", price: null, expires: "", category: "Otros" });
  });
  test("ignora fechas imposibles", () => {
    expect(parseLabelText("LECHE\nVENCE 45/13/2026").expires).toBe("");
  });
});
