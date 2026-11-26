const DAY_MS = 24 * 60 * 60 * 1000;

export function limaTodayISO(now = new Date()) {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-US", {
      timeZone: "America/Lima", year: "numeric", month: "2-digit", day: "2-digit",
    }).formatToParts(now).map(({ type, value }) => [type, value]),
  );
  return `${parts.year}-${parts.month}-${parts.day}`;
}

export function daysUntilExpiry(expiryDate, today = limaTodayISO()) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(expiryDate || "")) return null;
  const difference = Date.parse(`${expiryDate}T00:00:00Z`) - Date.parse(`${today}T00:00:00Z`);
  return Number.isFinite(difference) ? Math.round(difference / DAY_MS) : null;
}

const normalize = (value) => String(value || "")
  .normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es-PE");

export function filterOffers(offers, filters, today = limaTodayISO()) {
  const query = normalize(filters.query).trim();
  const minPrice = filters.minPrice === "" ? null : Number(filters.minPrice);
  const maxPrice = filters.maxPrice === "" ? null : Number(filters.maxPrice);
  const maxDays = filters.maxDays === "" ? null : Number(filters.maxDays);

  return offers.filter((offer) => {
    const price = Number(offer.current_price);
    const days = daysUntilExpiry(offer.expiry_date, today);
    if (filters.storeId !== null && filters.storeId !== undefined && offer.store_id !== filters.storeId) return false;
    if (query && !normalize(`${offer.product_name} ${offer.category} ${offer.store_name}`).includes(query)) return false;
    if (!Number.isFinite(price) || (minPrice !== null && price < minPrice) ||
        (maxPrice !== null && price > maxPrice)) return false;
    if (maxDays !== null && (days === null || days < 0 || days > maxDays)) return false;
    return true;
  });
}

export function sortOffersByPrice(offers, order) {
  if (order !== "asc" && order !== "desc") return offers;
  const direction = order === "asc" ? 1 : -1;
  return [...offers].sort((a, b) => direction * (Number(a.current_price) - Number(b.current_price)) || a.id - b.id);
}

export function groupOffersByStore(stores, offers, includeEmpty = false, priceOrder = "none") {
  const byStore = new Map(stores.map((store) => [store.id, { ...store, offers: [] }]));
  for (const offer of offers) byStore.get(offer.store_id)?.offers.push(offer);
  const groups = [...byStore.values()].filter((store) => includeEmpty || store.offers.length > 0);
  if (priceOrder === "asc" || priceOrder === "desc") {
    const direction = priceOrder === "asc" ? 1 : -1;
    groups.sort((a, b) => {
      if (!a.offers.length) return 1;
      if (!b.offers.length) return -1;
      return direction * (Number(a.offers[0].current_price) - Number(b.offers[0].current_price)) || a.id - b.id;
    });
  }
  return groups;
}
