import { detectCategory, fold, fullYear, isoDate, stem } from "./textTools";

const UNITS = { un: 1, uno: 1, una: 1, dos: 2, tres: 3, cuatro: 4, cinco: 5, seis: 6, siete: 7, ocho: 8, nueve: 9, diez: 10, once: 11, doce: 12, trece: 13, catorce: 14, quince: 15, dieciseis: 16, diecisiete: 17, dieciocho: 18, diecinueve: 19, veinte: 20, veintiuno: 21, veintidos: 22, veintitres: 23, veinticuatro: 24, veinticinco: 25, veintiseis: 26, veintisiete: 27, veintiocho: 28, veintinueve: 29 };
const TENS = { treinta: 30, cuarenta: 40, cincuenta: 50, sesenta: 60, setenta: 70, ochenta: 80, noventa: 90 };
const MONTHS = { enero: 1, febrero: 2, marzo: 3, abril: 4, mayo: 5, junio: 6, julio: 7, agosto: 8, septiembre: 9, setiembre: 9, octubre: 10, noviembre: 11, diciembre: 12 };
const MEASURES = [[/^(kilos?|kilogramos?|kg)$/, "kg"], [/^(litros?|lt|l)$/, "litro"], [/^(paquetes?|paq)$/, "paq."], [/^(cajas?)$/, "caja"], [/^(unidades|unidad|unid)$/, "unid."]];
const FILLER_START = /^(?:por favor\s+)?(?:agrega(?:r|me)?|anade|anadir|registra(?:r|me)?|ingresa(?:r)?|pon(?:er|me)?|llegaron|entraron|compre|vende(?:r|me)?|vendi|cobra(?:r|me)?|venta de|nueva venta de)\s+/;
const STOP_WORDS = new Set(["de", "del", "la", "el", "los", "las", "en", "con", "para"]);
const NUMBER = "\\d+(?:[.,]\\d+)?";
const WORD_NUMBER = `(?:${[...Object.keys(TENS), ...Object.keys(UNITS)].join("|")})`;

function joinCompoundNumbers(text) {
  return text
    .replace(new RegExp(`\\b(${Object.keys(TENS).join("|")})\\s+y\\s+(${Object.keys(UNITS).filter((word) => UNITS[word] < 10).join("|")})\\b`, "g"), (_, ten, unit) => String(TENS[ten] + UNITS[unit]))
    .replace(new RegExp(`\\b(${Object.keys(TENS).join("|")})\\b`, "g"), (word) => String(TENS[word]));
}

function numberValue(word) {
  if (word in UNITS) return UNITS[word];
  if (word in TENS) return TENS[word];
  const value = Number(String(word).replace(",", "."));
  return Number.isFinite(value) ? value : null;
}

function normalized(text) {
  return joinCompoundNumbers(fold(text).replace(/\s+/g, " ").trim()).replace(/[¿?¡!;]/g, "").replace(/\.$/, "");
}

function extractExpiry(text, today) {
  const numeric = text.match(/(?:vence[n]?(?:\s+el)?|vencimiento(?:\s+el)?)\s+(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})/);
  if (numeric) return { expires: isoDate(Number(numeric[1]), Number(numeric[2]), fullYear(numeric[3])), text: text.replace(numeric[0], " ") };
  const spoken = text.match(new RegExp(`(?:que\\s+)?(?:vence[n]?|vencimiento)(?:\\s+el)?\\s+(\\d{1,2}|${WORD_NUMBER})\\s+de\\s+(${Object.keys(MONTHS).join("|")})(?:\\s+(?:de|del)\\s+(\\d{4}))?`));
  if (!spoken) return { expires: "", text: text.replace(/\bque\s*$/, "") };
  const day = numberValue(spoken[1]);
  const month = MONTHS[spoken[2]];
  let year = spoken[3] ? Number(spoken[3]) : Number(today.slice(0, 4));
  let expires = isoDate(day, month, year);
  if (expires && !spoken[3] && expires < today) {
    year += 1;
    expires = isoDate(day, month, year);
  }
  return { expires, text: text.replace(spoken[0], " ") };
}

function extractPrice(text) {
  const amount = `(${NUMBER}|${WORD_NUMBER})`;
  const withSoles = text.match(new RegExp(`(?:\\b(?:a|por|cuesta|vale|precio(?:\\s+de)?)\\s+)?(?:s/\\.?\\s*)?${amount}\\s+(?:soles?)(?:\\s+con\\s+${amount}(?:\\s+centimos?)?)?`));
  if (withSoles) {
    const whole = numberValue(withSoles[1]);
    const cents = withSoles[2] ? numberValue(withSoles[2]) : 0;
    return { price: Math.round((whole + cents / 100) * 100) / 100, text: text.replace(withSoles[0], " ") };
  }
  const labelled = text.match(new RegExp(`\\b(?:cuesta|vale|precio(?:\\s+de)?)\\s+(?:s/\\.?\\s*)?${amount}`));
  if (labelled) return { price: numberValue(labelled[1]), text: text.replace(labelled[0], " ") };
  const decimal = text.match(/\ba\s+(\d+[.,]\d{1,2})\b/);
  if (decimal) return { price: numberValue(decimal[1]), text: text.replace(decimal[0], " ") };
  return { price: null, text };
}

function measureOf(word) {
  return MEASURES.find(([pattern]) => pattern.test(word))?.[1] || null;
}

function extractQuantity(text) {
  const words = text.trim().split(/\s+/).filter(Boolean);
  let quantity = null;
  let unit = null;
  if (words[0] === "medio" || words[0] === "media") {
    quantity = 0.5;
    words.shift();
  } else if (words.length > 1 && numberValue(words[0]) !== null && (/^\d/.test(words[0]) || words[0] in UNITS)) {
    quantity = numberValue(words.shift());
  }
  if (words[0] && measureOf(words[0])) unit = measureOf(words.shift());
  if (words[0] === "de" || words[0] === "del") words.shift();
  return { quantity, unit, rest: words.join(" ") };
}

// Conserva tildes y mayúsculas originales ubicando el nombre en el texto dictado.
function originalName(source, foldedName) {
  if (!foldedName) return "";
  const words = source.trim().split(/\s+/);
  const target = foldedName.split(" ");
  for (let start = 0; start <= words.length - target.length; start += 1) {
    if (target.every((word, index) => fold(words[start + index]).replace(/[.,]$/, "") === word)) {
      const name = words.slice(start, start + target.length).join(" ").replace(/[.,]$/, "");
      return name.charAt(0).toUpperCase() + name.slice(1).toLowerCase();
    }
  }
  return foldedName.charAt(0).toUpperCase() + foldedName.slice(1);
}

export function parseProductSpeech(text, today) {
  const base = normalized(text).replace(FILLER_START, "");
  const expiry = extractExpiry(base, today);
  const price = extractPrice(expiry.text);
  const { quantity, unit, rest } = extractQuantity(price.text.replace(/\s+/g, " "));
  const foldedName = rest.replace(/\b(?:que|y)\s*$/, "").trim();
  const name = originalName(text, foldedName);
  return { name, quantity, unit: unit || "unid.", price: price.price, expires: expiry.expires, category: detectCategory(name) };
}

function significantStems(text) {
  return fold(text).split(/[^a-z0-9]+/).filter((word) => word && !STOP_WORDS.has(word)).map(stem);
}

function matchProducts(heard, products) {
  const wanted = significantStems(heard);
  if (!wanted.length) return [];
  return products.filter((product) => {
    const available = significantStems(product.name);
    return wanted.every((word) => available.includes(word));
  });
}

export function parseSaleSpeech(text, products) {
  const sellable = products.filter((product) => product.activo !== false);
  const body = normalized(text).replace(FILLER_START, "");
  const result = { lines: [], ambiguous: [], unknown: [] };
  for (const segment of body.split(/\s*(?:,|\by\b|\bmas\b)\s*/).filter(Boolean)) {
    const { quantity, rest } = extractQuantity(segment);
    const heard = rest.trim();
    if (!heard) continue;
    const matches = matchProducts(heard, sellable);
    if (matches.length === 1) result.lines.push({ productId: matches[0].id, quantity: quantity ?? 1, heard });
    else if (matches.length > 1) result.ambiguous.push({ heard, quantity: quantity ?? 1, productIds: matches.map((product) => product.id) });
    else result.unknown.push(heard);
  }
  return result;
}
