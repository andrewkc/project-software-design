export const starterProducts = [
  { id: 1, name: "Leche Gloria entera", category: "Lácteos", icon: "\u{1F95B}", stock: 8, unit: "unid.", price: 4.5, expires: "2026-10-20" },
  { id: 2, name: "Yogurt natural", category: "Lácteos", icon: "\u{1F95B}", stock: 5, unit: "unid.", price: 3.8, expires: "2026-10-21" },
  { id: 3, name: "Plátano de seda", category: "Frutas", icon: "\u{1F34C}", stock: 12, unit: "kg", price: 3.5, expires: "2026-10-22" },
  { id: 4, name: "Arroz extra", category: "Abarrotes", icon: "\u{1F35A}", stock: 24, unit: "unid.", price: 4.2, expires: "2027-06-10" },
  { id: 5, name: "Gaseosa familiar", category: "Bebidas", icon: "\u{1F964}", stock: 10, unit: "unid.", price: 7.5, expires: "" },
  { id: 6, name: "Detergente en polvo", category: "Limpieza", icon: "\u{1F9FC}", stock: 6, unit: "unid.", price: 8.9, expires: "" },
  { id: 7, name: "Galletas de soda", category: "Snacks", icon: "\u{1F36A}", stock: 15, unit: "unid.", price: 2.5, expires: "2027-01-15" },
  { id: 8, name: "Atún en lata", category: "Conservas", icon: "\u{1F96B}", stock: 9, unit: "unid.", price: 6.4, expires: "2028-03-20" },
  { id: 9, name: "Jabón de tocador", category: "Cuidado personal", icon: "\u{1F9FC}", stock: 7, unit: "unid.", price: 3.2, expires: "" },
  { id: 10, name: "Agua mineral", category: "Bebidas", icon: "\u{1F964}", stock: 18, unit: "unid.", price: 2.5, expires: "" },
  { id: 11, name: "Leche chocolatada", category: "Lácteos", icon: "\u{1F95B}", stock: 8, unit: "unid.", price: 4.8, expires: "2027-02-10" },
  { id: 12, name: "Yogurt de fresa", category: "Lácteos", icon: "\u{1F95B}", stock: 6, unit: "unid.", price: 4.2, expires: "2027-01-28" },
  { id: 13, name: "Manzana roja", category: "Frutas", icon: "\u{1F34E}", stock: 14, unit: "kg", price: 4.5, expires: "2026-12-10" },
  { id: 14, name: "Fideos largos", category: "Abarrotes", icon: "\u{1F35C}", stock: 20, unit: "unid.", price: 3.2, expires: "2028-01-12" },
  { id: 15, name: "Lejía", category: "Limpieza", icon: "\u{1F9FC}", stock: 5, unit: "unid.", price: 4.9, expires: "" },
  { id: 16, name: "Papas fritas", category: "Snacks", icon: "\u{1F35F}", stock: 11, unit: "unid.", price: 3.5, expires: "2027-04-18" },
  { id: 17, name: "Sardinas en lata", category: "Conservas", icon: "\u{1F96B}", stock: 7, unit: "unid.", price: 5.8, expires: "2028-04-20" },
  { id: 18, name: "Shampoo familiar", category: "Cuidado personal", icon: "\u{1F9F4}", stock: 4, unit: "unid.", price: 12.5, expires: "" },
  { id: 19, name: "Jugo de naranja", category: "Bebidas", icon: "\u{1F9C3}", stock: 9, unit: "unid.", price: 5.5, expires: "2027-03-12" },
  { id: 20, name: "Avena en hojuelas", category: "Abarrotes", icon: "\u{1F35A}", stock: 13, unit: "unid.", price: 4.1, expires: "2028-02-08" },
  { id: 21, name: "Queso fresco", category: "Lácteos", icon: "\u{1F9C0}", stock: 4, unit: "unid.", price: 8.5, expires: "2026-11-20" },
  { id: 22, name: "Tomate italiano", category: "Frutas", icon: "\u{1F345}", stock: 6, unit: "kg", price: 4.2, expires: "2026-11-21" },
  { id: 23, name: "Pan de molde", category: "Abarrotes", icon: "\u{1F35E}", stock: 5, unit: "unid.", price: 6.9, expires: "2026-11-22" },
  { id: 24, name: "Jugo de mango", category: "Bebidas", icon: "\u{1F9C3}", stock: 8, unit: "unid.", price: 5.9, expires: "2026-11-23" },
  { id: 25, name: "Jamón cocido", category: "Conservas", icon: "\u{1F953}", stock: 3, unit: "unid.", price: 9.8, expires: "2026-11-24" },
  { id: 26, name: "Crema corporal", category: "Cuidado personal", icon: "\u{1F9F4}", stock: 4, unit: "unid.", price: 11.5, expires: "2026-11-25" },
];

export const productMethods = [
  { id: "photo", title: "Toma una foto", subtitle: "De tu mercader\u00eda o boleta", icon: "camera", tint: "peach", tag: "Con imagen" },
  { id: "voice", title: "Habla para registrar", subtitle: "Cu\u00e9ntanos qu\u00e9 ingres\u00f3", icon: "mic", tint: "lavender", tag: "Manos libres" },
  { id: "text", title: "Escribe para registrar", subtitle: "Agrega los datos a tu ritmo", icon: "edit", tint: "mint", tag: "Manual" },
  { id: "scan", title: "Escanea un producto", subtitle: "Usa el c\u00f3digo de barras", icon: "scan", tint: "yellow", tag: "C\u00f3digo de barras" },
];

export const navigation = [
  { id: "home", label: "Inicio", icon: "home" },
  { id: "inventory", label: "Inventario", icon: "box" },
  { id: "register", label: "Registrar", icon: "plus" },
  { id: "alerts", label: "Vencimientos", icon: "calendar" },
];

export const mobileNavigation = [
  { id: "home", label: "Inicio", icon: "home" },
  { id: "inventory", label: "Inventario", icon: "box" },
  { id: "register", label: "Registrar", icon: "plus" },
  { id: "alerts", label: "Vencimientos", icon: "calendar" },
  { id: "profile", label: "Perfil", icon: "users" },
];
