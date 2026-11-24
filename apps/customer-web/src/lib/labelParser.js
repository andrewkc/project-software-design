import { detectCategory, fold, fullYear, isoDate } from "./textTools";

const DATE = /(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})/g;
const EXPIRY_WORDS = /\b(vence|venc|vto|vcto|exp|expira|fv|f\.?v\.?|consumir)\b/;
const DATA_LINE = /\b(ingredientes?|lote|fab|fabricacion|vence|venc|vto|vcto|exp|expira|fv|peso|neto|contenido|registro|rs|ruc|precio|consumir)\b|s\/|\d{2,}/;

function datesIn(line) {
  return [...line.matchAll(DATE)].map((match) => isoDate(Number(match[1]), Number(match[2]), fullYear(match[3]))).filter(Boolean);
}

function findExpiry(lines) {
  const marked = lines.filter((line) => EXPIRY_WORDS.test(fold(line))).flatMap(datesIn);
  if (marked.length) return marked.sort().at(-1);
  const hasInvalidMarked = lines.some((line) => EXPIRY_WORDS.test(fold(line)));
  if (hasInvalidMarked) return "";
  return lines.filter((line) => !/\bfab/.test(fold(line))).flatMap(datesIn).sort().at(-1) || "";
}

function findPrice(text) {
  const match = text.match(/s\/\.?\s*(\d+(?:[.,]\d{1,2})?)/i);
  return match ? Number(match[1].replace(",", ".")) : null;
}

function isNameLine(line) {
  const letters = line.match(/\p{L}/gu)?.length || 0;
  return letters >= 3 && letters / line.replace(/\s/g, "").length >= 0.7 && !DATA_LINE.test(fold(line));
}

function titleCase(line) {
  return line.toLowerCase().replace(/(^|\s)(\p{L})/gu, (_, space, letter) => space + letter.toUpperCase());
}

export function parseLabelText(text) {
  const lines = String(text || "").split(/\r?\n/).map((line) => line.trim().replace(/\s+/g, " ")).filter(Boolean);
  const nameLine = lines.find(isNameLine);
  const name = nameLine ? titleCase(nameLine) : "";
  return { name, price: findPrice(text || ""), expires: findExpiry(lines), category: detectCategory(name) };
}
