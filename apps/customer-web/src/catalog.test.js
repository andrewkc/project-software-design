import test from "node:test";
import assert from "node:assert/strict";
import { daysUntilExpiry, filterOffers, groupOffersByStore, limaTodayISO, sortOffersByPrice } from "./catalog.js";

const today = "2026-11-25";
const offers = [
  { id: 1, store_id: 1, store_name: "Mercado Verde", product_name: "Yogurt natural", category: "Lácteos", current_price: "3.50", expiry_date: "2026-12-05" },
  { id: 2, store_id: 2, store_name: "Despensa Cercana", product_name: "Yogurt de fresa", category: "Lácteos", current_price: "4.20", expiry_date: "2026-12-07" },
  { id: 3, store_id: 2, store_name: "Despensa Cercana", product_name: "Manzana roja", category: "Frutas", current_price: "2.80", expiry_date: "2026-11-28" },
];

test("el día de vencimiento se calcula con fecha de Lima y límite inclusivo", () => {
  assert.equal(limaTodayISO(new Date("2026-11-26T02:00:00Z")), today);
  assert.equal(daysUntilExpiry("2026-12-05", today), 10);
  assert.equal(daysUntilExpiry("2026-11-25", today), 0);
});

test("la búsqueda general encuentra el mismo producto en distintas bodegas", () => {
  assert.deepEqual(filterOffers(offers, { query: "YOGURT", minPrice: "", maxPrice: "", maxDays: "" }, today).map((offer) => offer.id), [1, 2]);
});

test("búsqueda sin tildes coincide con nombres acentuados", () => {
  assert.deepEqual(filterOffers(offers, { query: "lacteos", minPrice: "", maxPrice: "", maxDays: "" }, today).map((offer) => offer.id), [1, 2]);
});

test("mínimo y máximo de precio incluyen los límites", () => {
  assert.deepEqual(filterOffers(offers, { query: "", minPrice: "3.50", maxPrice: "4.20", maxDays: "" }, today).map((offer) => offer.id), [1, 2]);
});

test("vencimiento en máximo diez días excluye productos de once o más", () => {
  assert.deepEqual(filterOffers(offers, { query: "", minPrice: "", maxPrice: "", maxDays: "10" }, today).map((offer) => offer.id), [1, 3]);
});

test("seleccionar una bodega conserva solo sus productos", () => {
  assert.deepEqual(filterOffers(offers, { query: "", minPrice: "", maxPrice: "", maxDays: "", storeId: 2 }, today).map((offer) => offer.id), [2, 3]);
});

test("la búsqueda vacía agrupa por tienda y conserva sus precios", () => {
  const stores = [{ id: 1, nombre: "Mercado Verde" }, { id: 2, nombre: "Despensa Cercana" }, { id: 3, nombre: "Sin ofertas" }];
  const grouped = groupOffersByStore(stores, offers, true);
  assert.deepEqual(grouped.map((store) => store.offers.map((offer) => offer.id)), [[1], [2, 3], []]);
  assert.equal(grouped[0].offers[0].current_price, "3.50");
});

test("precio menor y mayor ordenan productos sin alterar la lista original", () => {
  assert.deepEqual(sortOffersByPrice(offers, "asc").map((offer) => offer.id), [3, 1, 2]);
  assert.deepEqual(sortOffersByPrice(offers, "desc").map((offer) => offer.id), [2, 1, 3]);
  assert.deepEqual(offers.map((offer) => offer.id), [1, 2, 3]);
});

test("al ordenar por precio, las bodegas siguen el precio de sus productos", () => {
  const stores = [{ id: 1, nombre: "Mercado Verde" }, { id: 2, nombre: "Despensa Cercana" }];
  const ascending = groupOffersByStore(stores, sortOffersByPrice(offers, "asc"), false, "asc");
  const descending = groupOffersByStore(stores, sortOffersByPrice(offers, "desc"), false, "desc");
  assert.deepEqual(ascending.map((store) => store.id), [2, 1]);
  assert.deepEqual(ascending[0].offers.map((offer) => offer.id), [3, 2]);
  assert.deepEqual(descending.map((store) => store.id), [2, 1]);
  assert.deepEqual(descending[0].offers.map((offer) => offer.id), [2, 3]);
});
