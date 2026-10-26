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

