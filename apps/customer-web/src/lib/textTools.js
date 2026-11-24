// Utilidades compartidas por los intérpretes de voz y de etiquetas.

const CATEGORY_KEYWORDS = [
  ["Lácteos", ["leche", "yogurt", "yogur", "queso", "mantequilla"]],
  ["Frutas", ["manzana", "platano", "naranja", "mandarina", "uva", "fresa", "mango", "pera", "tomate", "limon", "papaya", "pina"]],
  ["Bebidas", ["gaseosa", "agua", "jugo", "cerveza", "refresco", "cafe", "te"]],
  ["Limpieza", ["detergente", "lejia", "lavavajilla", "desinfectante", "escoba"]],
  ["Snacks", ["galleta", "papas fritas", "chocolate", "caramelo", "chifle", "snack"]],
  ["Conservas", ["atun", "sardina", "conserva", "jamon", "durazno en"]],
  ["Cuidado personal", ["jabon", "shampoo", "champu", "crema", "pasta dental", "desodorante"]],
  ["Abarrotes", ["arroz", "azucar", "fideo", "aceite", "avena", "harina", "sal", "lenteja", "frejol", "pan", "menestra"]],
];

export function fold(text) {
  return String(text ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

export function stem(word) {
  // leche/leches y atun/atunes deben llegar a la misma raíz.
  const singular = word.length > 3 && word.endsWith("s") ? word.slice(0, -1) : word;
  return singular.length > 3 && singular.endsWith("e") ? singular.slice(0, -1) : singular;
}

export function detectCategory(name) {
  const words = fold(name).split(/[^a-z0-9]+/).map(stem);
  const folded = fold(name);
  const match = CATEGORY_KEYWORDS.find(([, keywords]) => keywords.some((keyword) => (keyword.includes(" ") ? folded.includes(keyword) : words.includes(stem(keyword)))));
  return match ? match[0] : "Otros";
}

export function isoDate(day, month, year) {
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return "";
  return date.toISOString().slice(0, 10);
}

export function fullYear(value) {
  const year = Number(value);
  return year < 100 ? 2000 + year : year;
}
