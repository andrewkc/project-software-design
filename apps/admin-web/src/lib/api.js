// Browser contract for the isolated /admin backend router.
// The Gemini key and every write decision stay in the backend; this client
// only sends the Bearer token returned by /admin/auth/login.

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "bodesmart-admin-token";

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

export const adminApi = {
  login: (payload) => request("/admin/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  me: () => request("/admin/me"),
  listUsers: () => request("/admin/users"),
  listStores: () => request("/admin/stores"),
  createUser: (payload) => request("/admin/users", { method: "POST", body: JSON.stringify(payload) }),
  updateUser: (id, payload) => request(`/admin/users/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deactivateUser: (id) => request(`/admin/users/${encodeURIComponent(id)}`, { method: "DELETE" }),
};
