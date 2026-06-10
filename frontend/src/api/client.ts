const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const resp = await fetch(url, init);
  if (!resp.ok) {
    let detail: unknown = null;
    try {
      detail = await resp.json();
    } catch {
      detail = await resp.text();
    }
    throw new ApiError(
      resp.status,
      `${resp.status} ${resp.statusText} on ${path}`,
      detail,
    );
  }
  // 204 No Content
  if (resp.status === 204) {
    return undefined as T;
  }
  return resp.json();
}

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}
