import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { InteractionRequiredAuthError } from "@azure/msal-browser";
import { clearAuthStorage, getAccessToken, saveAuthStorage } from "../../services/authStorage";
import { fetchCurrentUser } from "../../features/auth/auth.api";
import type { AppUser, AuthState } from "../../features/auth/auth.types";
import {
  ensureMsalInitialized,
  isRealEntraConfigured,
  loginRequest,
  msalInstance
} from "../../services/msal";

const mockAuthEnabled = (import.meta.env.VITE_MOCK_AUTH ?? "false") === "true";
const legacyMockToken = "mock-token";

const mockUser: AppUser = {
  oid: "dev-bypass-oid",
  email: "dev.user@example.com",
  displayName: "Dev User",
  isAdmin: true
};

type AuthContextValue = AuthState & {
  login: () => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    status: "loading",
    user: null,
    accessToken: getAccessToken()
  });

  const hydrate = async () => {
    if (mockAuthEnabled) {
      const storedUser = window.localStorage.getItem("azure_ai_ops_user");
      const user = storedUser ? (JSON.parse(storedUser) as AppUser) : null;

      if (user) {
        setState({ status: "authenticated", user, accessToken: getAccessToken() ?? "mock-token" });
      } else {
        setState({ status: "unauthenticated", user: null, accessToken: null });
      }
      return;
    }

    try {
      if (getAccessToken() === legacyMockToken) {
        clearAuthStorage();
      }

      await ensureMsalInitialized();
      const redirectResult = await msalInstance.handleRedirectPromise();
      const account = redirectResult?.account ?? msalInstance.getActiveAccount() ?? msalInstance.getAllAccounts()[0] ?? null;

      if (!account) {
        setState({ status: "unauthenticated", user: null, accessToken: null });
        return;
      }

      msalInstance.setActiveAccount(account);

      const tokenResult = redirectResult?.accessToken
        ? redirectResult
        : await msalInstance.acquireTokenSilent({
            ...loginRequest,
            account
          }).catch(async (error) => {
            if (error instanceof InteractionRequiredAuthError) {
              await msalInstance.acquireTokenRedirect({
                ...loginRequest,
                account
              });
            }
            throw error;
          });

      const accessToken = tokenResult?.accessToken ?? null;
      if (accessToken) {
        saveAuthStorage(accessToken);
      }

      const apiUser = await fetchCurrentUser();
      setState({
        status: "authenticated",
        user: apiUser,
        accessToken
      });
    } catch {
      setState({ status: "unauthenticated", user: null, accessToken: null });
    }
  };

  useEffect(() => {
    void hydrate();
  }, []);

  const login = async () => {
    if (mockAuthEnabled) {
      saveAuthStorage(legacyMockToken);
      window.localStorage.setItem("azure_ai_ops_user", JSON.stringify(mockUser));
      setState({ status: "authenticated", user: mockUser, accessToken: legacyMockToken });
      return;
    }

    if (!isRealEntraConfigured) {
      throw new Error("Microsoft sign-in is not configured");
    }

    clearAuthStorage();
    await ensureMsalInitialized();
    await msalInstance.loginRedirect(loginRequest);
  };

  const logout = async () => {
    clearAuthStorage();
    window.localStorage.removeItem("azure_ai_ops_user");

    if (mockAuthEnabled) {
      setState({ status: "unauthenticated", user: null, accessToken: null });
      return;
    }

    if (!isRealEntraConfigured) {
      setState({ status: "unauthenticated", user: null, accessToken: null });
      return;
    }

    await ensureMsalInitialized();
    const activeAccount = msalInstance.getActiveAccount() ?? msalInstance.getAllAccounts()[0] ?? null;
    if (activeAccount) {
      await msalInstance.logoutRedirect({
        account: activeAccount,
        postLogoutRedirectUri: window.location.origin
      });
      return;
    }

    setState({ status: "unauthenticated", user: null, accessToken: null });
  };

  const refreshUser = async () => {
    if (mockAuthEnabled) {
      const user = JSON.parse(window.localStorage.getItem("azure_ai_ops_user") ?? "null") as AppUser | null;
      if (user) {
        setState((current) => ({ ...current, status: "authenticated", user }));
      }
      return;
    }

    if (!isRealEntraConfigured) {
      setState({ status: "unauthenticated", user: null, accessToken: null });
      return;
    }

    await ensureMsalInitialized();
    const activeAccount = msalInstance.getActiveAccount() ?? msalInstance.getAllAccounts()[0] ?? null;
    if (!activeAccount) {
      setState({ status: "unauthenticated", user: null, accessToken: null });
      return;
    }

    msalInstance.setActiveAccount(activeAccount);

    const tokenResult = await msalInstance.acquireTokenSilent({
      ...loginRequest,
      account: activeAccount
    });

    saveAuthStorage(tokenResult.accessToken);

    const apiUser = await fetchCurrentUser();
    setState({
      status: "authenticated",
      user: apiUser,
      accessToken: tokenResult.accessToken
    });
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      login,
      logout,
      refreshUser
    }),
    [state]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
