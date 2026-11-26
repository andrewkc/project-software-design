const BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const TOKEN = "bodesmart_customer_token";

export const token = () => localStorage.getItem(TOKEN);
export const saveToken = (value) => value ? localStorage.setItem(TOKEN, value) : localStorage.removeItem(TOKEN);

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (token()) headers.Authorization = `Bearer ${token()}`;
  let response;
  try {
    response = await fetch(`${BASE}/customer${path}`, { ...options, headers });
  } catch {
    throw new Error("No se pudo conectar con BodeSmart. Comprueba que el servidor esté encendido.");
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "No se pudo completar la solicitud.");
  return body;
}

const post = (path, data) => request(path, { method: "POST", body: JSON.stringify(data) });
export const api = {
  stores: () => request("/stores"),
  offers: (storeId) => request("/offers" + (storeId ? `?store_id=${storeId}` : "")),
  register: (data) => post("/auth/register", data),
  login: (data) => post("/auth/login", data),
  me: () => request("/auth/me"),
  orders: () => request("/orders"),
  order: (id) => request(`/orders/${id}`),
  createOrder: (data) => post("/orders", data),
  simulatePayment: (id) => post(`/orders/${id}/simulate-payment`, {}),
  checkout: (id) => post(`/orders/${id}/checkout`, {}),
  verifyPayment: (id) => post(`/orders/${id}/verify-payment`, {}),
};
