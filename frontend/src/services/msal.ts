import { PublicClientApplication, type Configuration } from "@azure/msal-browser";

const isMockAuth = import.meta.env.VITE_MOCK_AUTH === "true";
const clientId = import.meta.env.VITE_ENTRA_CLIENT_ID?.trim() ?? "";
const tenantId = import.meta.env.VITE_ENTRA_TENANT_ID?.trim() ?? "";
const redirectUri =
  import.meta.env.VITE_ENTRA_REDIRECT_URI?.trim() ?? `${window.location.origin}/auth/callback`;
const apiScope = import.meta.env.VITE_ENTRA_API_SCOPE?.trim() ?? "";
const extraScopes = (import.meta.env.VITE_ENTRA_SCOPES ?? "")
  .split(",")
  .map((scope: string) => scope.trim())
  .filter(Boolean);

export const isRealEntraConfigured = !isMockAuth && Boolean(clientId) && Boolean(tenantId) && Boolean(apiScope);

if (!isMockAuth && import.meta.env.PROD && !isRealEntraConfigured) {
  throw new Error(
    "VITE_ENTRA_CLIENT_ID, VITE_ENTRA_TENANT_ID, and VITE_ENTRA_API_SCOPE are required for production frontend builds."
  );
}

export const msalConfig: Configuration = {
  auth: {
    clientId,
    authority: `https://login.microsoftonline.com/${tenantId || "common"}`,
    redirectUri
  },
  cache: {
    cacheLocation: "localStorage",
    storeAuthStateInCookie: false
  }
};

export const msalInstance = new PublicClientApplication(msalConfig);
export const msalInitialized = msalInstance.initialize();

export async function ensureMsalInitialized() {
  await msalInitialized;
}

export const loginRequest = {
  scopes: [apiScope, ...extraScopes]
};
