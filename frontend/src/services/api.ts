import { getAccessToken } from "./authStorage";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();

const baseUrl = (
  apiBaseUrl ??
  (import.meta.env.DEV ? "http://localhost:8000/api/v1" : "")
).replace(/\/$/, "");

if (!baseUrl) {
  throw new Error("VITE_API_BASE_URL is required for production frontend builds.");
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", headers.get("Content-Type") ?? "application/json");

  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with ${response.status}`);
  }

  return (await response.json()) as T;
}
