// src/lib/api.ts
export type SiteRecord = {
  id: number;
  url: string;
  name: string;
  ping_interval: number;
  com?: Record<string, unknown> | null;
};

//asdsadfa

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Ошибка API: ${res.status} ${res.statusText} → ${errText}`);
  }

  return res.json() as Promise<T>;
}

export function fetchSites() {
  return request<SiteRecord[]>("/sites");
}

export function createSite(url: string, name: string, ping_interval = 30) {
  return request<SiteRecord>("/sites", {
    method: "POST",
    body: JSON.stringify({ url, name, ping_interval }),
  });
}

export function updateSite(id: number, data: { url: string; name: string; ping_interval: number }) {
  return request<SiteRecord>(`/sites/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteSite(id: number) {
  return request<{ ok: boolean }>(`/sites/${id}`, { method: "DELETE" }).then(() => true);
}

export function patchSiteParams(id: number, params: { com?: Record<string, unknown> | null }) {
  return request<SiteRecord>(`/sites/${id}/params`, {
    method: "PATCH",
    body: JSON.stringify(params),
  });
}
