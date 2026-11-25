// API contract for the backend that is still to be implemented.
// Tables involved: Bodega, Jefe, Empleado, Producto, ProductosBodega.
// The backend owns the current warehouse; the frontend only sends the token.
//
// Expected responses:
// - auth endpoints: { token, perfil }
// - GET /auth/me and GET /profiles: profile objects with { id, rol, nombres, apellidos, correo, bodegaNombre, activo }
// - GET/POST/PATCH /products: rows joined from Producto and ProductosBodega
//
// Product payloads use the database column names so the backend can map them directly.

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "bodesmart-token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request(path, options = {}) {
  const token = getToken();
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    if (response.status === 401) clearToken();
    const detail = data?.detail || data?.message || data;
    let message = `Error ${response.status}`;
    if (typeof detail === "string") message = detail;
    else if (Array.isArray(detail)) message = detail.map((item) => item.msg || JSON.stringify(item)).join(", ");
    else if (detail && typeof detail === "object") message = JSON.stringify(detail);
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return data;
}

function normalizeRole(raw) {
  const role = raw?.rol || raw?.role;
  return role === "empleado" ? "empleado" : "jefe";
}

export function toUser(raw) {
  if (!raw) return null;
  const nombres = raw.nombres || "";
  const apellidos = raw.apellidos || "";
  const name = raw.nombre || [nombres, apellidos].filter(Boolean).join(" ");
  return {
    id: raw.id,
    role: normalizeRole(raw),
    name,
    nombres,
    apellidos,
    email: raw.correo || raw.email || "",
    store: raw.bodegaNombre || raw.bodega?.nombre || raw.store || "",
    activo: raw.activo !== false,
  };
}

export function toProfile(raw) {
  return toUser(raw);
}

export function toProduct(raw) {
  return {
    id: raw.id ?? raw.id_producto,
    name: raw.nombre || raw.name || "",
    category: raw.categoria || raw.category || "",
    icon: raw.icono || raw.icon || "📦",
    stock: Number(raw.stock) || 0,
    unit: raw.unidad_medida || raw.unit || "unid.",
    price: Number(raw.precio_venta ?? raw.price) || 0,
    expires: raw.fecha_vencimiento || raw.expires || "",
    creadoPor: raw.creado_por ?? raw.creadoPor ?? null,
    bloqueado: Boolean(raw.bloqueado),
    bloqueadoPor: raw.bloqueado_por ?? raw.bloqueadoPor ?? null,
    activo: raw.estado !== "inactivo",
  };
}

export const api = {
  signup: (payload) => request("/auth/signup", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload) => request("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  getMe: () => request("/auth/me"),
  changePassword: (payload) => request("/auth/change-password", { method: "POST", body: JSON.stringify(payload) }),
  listProfiles: () => request("/profiles"),
  createEmployee: (payload) => request("/profiles/employees", { method: "POST", body: JSON.stringify(payload) }),
  revokeEmployee: (id) => request(`/profiles/employees/${encodeURIComponent(id)}/revoke`, { method: "POST" }),
  listProducts: () => request("/products"),
  createProduct: (payload) => request("/products", { method: "POST", body: JSON.stringify(payload) }),
  updateProduct: (id, payload) => request(`/products/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) }),
};
