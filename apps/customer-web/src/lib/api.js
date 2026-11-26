// Contrato público tomado del customer-web implementado por el compañero.
// La URL se hornea en el build; por defecto apunta al backend local.
const BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const TOKEN_KEY = "bodesmart_customer_token";

export const token = () => localStorage.getItem(TOKEN_KEY);
export const getToken = token;
export const saveToken = (value) => value ? localStorage.setItem(TOKEN_KEY, value) : localStorage.removeItem(TOKEN_KEY);

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
  paymentMethods: () => request("/payment-methods"),
  offers: (storeId, page = 1) => {
    const params = new URLSearchParams();
    if (storeId) params.set("store_id", storeId);
    if (page > 1) params.set("page", page);
    const query = params.toString();
    return request("/offers" + (query ? `?${query}` : ""));
  },
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
