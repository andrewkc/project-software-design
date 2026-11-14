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

async function apiSend(method, path, data, fetcher) {
  const csrfResponse = await fetcher("/api/v1/auth/csrf", { credentials: "same-origin" });
  if (!csrfResponse.ok) throw new Error("No se pudo preparar la sesión segura");
  const { csrf_token: csrfToken } = await csrfResponse.json();
  const response = await fetcher(`/api/v1${path}`, {
    method,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error(body.error?.message || `API ${response.status}`);
    error.code = body.error?.code;
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}

export function apiPost(path, data = {}, fetcher = fetch) {
  return apiSend("POST", path, data, fetcher);
}

export function apiPatch(path, data = {}, fetcher = fetch) {
  return apiSend("PATCH", path, data, fetcher);
}

export function apiDelete(path, fetcher = fetch) {
  return apiSend("DELETE", path, undefined, fetcher);
}
