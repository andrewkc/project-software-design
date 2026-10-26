// Single place for calls to the Python API. Browser cookies carry the session.
export async function apiGet(path, fetcher = fetch) {
  const response = await fetcher(`/api/v1${path}`, { credentials: "same-origin" });
  if (!response.ok) throw new Error(`API ${response.status}`);
  return response.json();
}

export function getApiHealth(fetcher) {
  return apiGet("/health", fetcher);
}

export function getStores(fetcher) {
  return apiGet("/stores", fetcher);
}

export async function apiPost(path, data = {}, fetcher = fetch) {
  const csrfResponse = await fetcher("/api/v1/auth/csrf", { credentials: "same-origin" });
  if (!csrfResponse.ok) throw new Error("No se pudo preparar la sesión segura");
  const { csrf_token: csrfToken } = await csrfResponse.json();
  const response = await fetcher(`/api/v1${path}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error?.message || `API ${response.status}`);
  }
  return response.status === 204 ? null : response.json();
}

