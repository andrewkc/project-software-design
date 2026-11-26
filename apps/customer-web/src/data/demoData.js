// Datos de demostración para que la tienda sea navegable sin backend.
// Se muestran solo cuando la API no responde; la UI lo indica explícitamente.
export const demoStores = [
  { id: 1, nombre: "Bodega San Miguel", direccion: "Jr. Lima 245, San Miguel" },
  { id: 2, nombre: "Bodega La Esquina", direccion: "Av. Sucre 180, Pueblo Libre" },
  { id: 3, nombre: "Bodega Los Olivos", direccion: "Calle París 512, Los Olivos" },
  { id: 4, nombre: "Bodega Miraflores", direccion: "Av. Larco 930, Miraflores" },
];

export const demoOffers = [
  { id: 101, store_id: 1, product_name: "Leche Gloria entera", category: "Lácteos", icon: "🥛", unit: "unid.", current_price: 4.5, original_price: 5.2, expiry_date: "2026-11-29", available: 8 },
  { id: 102, store_id: 1, product_name: "Yogurt natural", category: "Lácteos", icon: "🥛", unit: "unid.", current_price: 3.8, original_price: 4.4, expiry_date: "2026-12-02", available: 5 },
  { id: 103, store_id: 1, product_name: "Pan de molde", category: "Panadería", icon: "🍞", unit: "unid.", current_price: 6.9, original_price: 8.5, expiry_date: "2026-11-28", available: 4 },
  { id: 104, store_id: 2, product_name: "Manzana roja", category: "Frutas", icon: "🍎", unit: "kg", current_price: 4.5, original_price: 5.9, expiry_date: "2026-12-05", available: 12 },
  { id: 105, store_id: 2, product_name: "Tomate italiano", category: "Frutas", icon: "🍅", unit: "kg", current_price: 4.2, original_price: 5.5, expiry_date: "2026-12-01", available: 6 },
  { id: 106, store_id: 2, product_name: "Queso fresco", category: "Lácteos", icon: "🧀", unit: "unid.", current_price: 8.5, original_price: 10.9, expiry_date: "2026-11-30", available: 4 },
  { id: 107, store_id: 3, product_name: "Gaseosa familiar", category: "Bebidas", icon: "🥤", unit: "unid.", current_price: 7.5, original_price: 8.9, expiry_date: "2027-03-12", available: 10 },
  { id: 108, store_id: 3, product_name: "Galletas de soda", category: "Snacks", icon: "🍪", unit: "unid.", current_price: 2.5, original_price: 3.2, expiry_date: "2027-01-15", available: 15 },
  { id: 109, store_id: 3, product_name: "Jugo de naranja", category: "Bebidas", icon: "🧃", unit: "unid.", current_price: 5.5, original_price: 6.8, expiry_date: "2026-12-20", available: 9 },
  { id: 110, store_id: 4, product_name: "Atún en lata", category: "Conservas", icon: "🥫", unit: "unid.", current_price: 6.4, original_price: 7.6, expiry_date: "2028-03-20", available: 9 },
  { id: 111, store_id: 4, product_name: "Sardinas en lata", category: "Conservas", icon: "🥫", unit: "unid.", current_price: 5.8, original_price: 6.9, expiry_date: "2028-04-20", available: 7 },
  { id: 112, store_id: 4, product_name: "Agua mineral", category: "Bebidas", icon: "💧", unit: "unid.", current_price: 2.5, original_price: 3.0, expiry_date: "2027-08-10", available: 18 },
];
