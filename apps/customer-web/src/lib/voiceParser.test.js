import { describe, expect, test } from "vitest";
import { parseProductSpeech, parseSaleSpeech } from "./voiceParser";

const today = "2026-11-23";
const products = [
  { id: 1, name: "Leche Gloria entera", stock: 8, activo: true },
  { id: 2, name: "Leche chocolatada", stock: 8, activo: true },
  { id: 3, name: "Arroz extra", stock: 24, activo: true },
  { id: 4, name: "Plátano de seda", stock: 12, unit: "kg", activo: true },
  { id: 5, name: "Atún en lata", stock: 9, activo: true },
  { id: 6, name: "Lejía", stock: 5, activo: false },
];

describe("parseProductSpeech", () => {
  test("entiende cantidad en palabras, nombre, precio y vencimiento", () => {
    expect(parseProductSpeech("Agrega seis yogures naturales a 3.50 soles que vencen el 20 de diciembre", today)).toMatchObject({
      name: "Yogures naturales", quantity: 6, unit: "unid.", price: 3.5, expires: "2026-12-20", category: "Lácteos",
    });
  });
  test("entiende unidad de medida", () => {
    expect(parseProductSpeech("registra 3 kilos de manzana", today)).toMatchObject({ name: "Manzana", quantity: 3, unit: "kg", category: "Frutas" });
  });
  test("entiende soles con céntimos dictados", () => {
    expect(parseProductSpeech("dos cajas de galletas cuesta cuatro soles con cincuenta", today)).toMatchObject({ name: "Galletas", quantity: 2, unit: "caja", price: 4.5 });
  });
  test("acepta coma decimal", () => {
    expect(parseProductSpeech("arroz precio 4,20", today)).toMatchObject({ name: "Arroz", price: 4.2 });
  });
  test("una fecha sin año ya pasada pasa al año siguiente", () => {
    expect(parseProductSpeech("leche vence el 5 de enero", today).expires).toBe("2027-01-05");
  });
  test("acepta fecha numérica", () => {
    expect(parseProductSpeech("queso vence 15/12/2026", today).expires).toBe("2026-12-15");
  });
  test("no inventa datos que no se dijeron", () => {
    const result = parseProductSpeech("azúcar rubia", today);
    expect(result).toMatchObject({ name: "Azúcar rubia", quantity: null, price: null, expires: "" });
  });
  test("ignora una fecha imposible", () => {
    expect(parseProductSpeech("leche vence el 31 de febrero", today).expires).toBe("");
  });
  test("texto vacío no produce producto", () => {
    expect(parseProductSpeech("   ", today).name).toBe("");
  });
});

describe("parseSaleSpeech", () => {
  test("reconoce varios productos con cantidades", () => {
    expect(parseSaleSpeech("vende dos atunes y un arroz", products)).toEqual({
      lines: [{ productId: 5, quantity: 2, heard: "atunes" }, { productId: 3, quantity: 1, heard: "arroz" }], ambiguous: [], unknown: [],
    });
  });
  test("sin cantidad asume una unidad", () => {
    expect(parseSaleSpeech("arroz", products).lines).toEqual([{ productId: 3, quantity: 1, heard: "arroz" }]);
  });
  test("no parte números compuestos con y", () => {
    expect(parseSaleSpeech("treinta y dos arroz", products).lines[0].quantity).toBe(32);
  });
  test("entiende medio kilo", () => {
    expect(parseSaleSpeech("medio kilo de plátano", products).lines).toEqual([{ productId: 4, quantity: 0.5, heard: "platano" }]);
  });
  test("si varios productos coinciden pide elegir y no adivina", () => {
    const result = parseSaleSpeech("dos leches", products);
    expect(result.lines).toEqual([]);
    expect(result.ambiguous[0]).toMatchObject({ heard: "leches", quantity: 2 });
    expect(result.ambiguous[0].productIds).toEqual([1, 2]);
  });
  test("un detalle extra resuelve la ambigüedad", () => {
    expect(parseSaleSpeech("una leche chocolatada", products).lines[0].productId).toBe(2);
  });
  test("informa lo que no encontró", () => {
    expect(parseSaleSpeech("tres gaseosas y un arroz", products)).toMatchObject({ unknown: ["gaseosas"], lines: [{ productId: 3 }] });
  });
  test("no ofrece productos desactivados", () => {
    expect(parseSaleSpeech("una lejía", products).unknown).toEqual(["lejia"]);
  });
});
