const TOKEN_KEY = "azure_ai_ops_access_token";

export function getAccessToken() {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function saveAuthStorage(token: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearAuthStorage() {
  window.localStorage.removeItem(TOKEN_KEY);
}
