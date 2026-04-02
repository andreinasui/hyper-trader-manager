import { createSignal, createRoot, createEffect } from "solid-js";
import { api } from "~/lib/api";
import type { User } from "~/lib/types";

function createAuthStore() {
  const [user, setUser] = createSignal<User | null>(null);
  const [token, setToken] = createSignal<string | null>(localStorage.getItem("auth_token"));
  const [loading, setLoading] = createSignal(true);
  const [isInitialized, setIsInitialized] = createSignal(false);

  const authenticated = () => !!user() && !!token();
  const ready = () => !loading();

  // Persist token to localStorage
  createEffect(() => {
    const currentToken = token();
    if (currentToken) {
      localStorage.setItem("auth_token", currentToken);
    } else {
      localStorage.removeItem("auth_token");
    }
  });

  async function checkSetup(): Promise<boolean> {
    try {
      const status = await api.getSetupStatus();
      setIsInitialized(status.initialized);
      return status.initialized;
    } catch {
      setIsInitialized(false);
      return false;
    }
  }

  async function checkAuth(): Promise<void> {
    const currentToken = token();
    if (!currentToken) {
      setLoading(false);
      return;
    }

    try {
      const userData = await api.me();
      setUser(userData);
    } catch {
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  async function login(username: string, password: string): Promise<void> {
    const response = await api.login(username, password);
    setToken(response.access_token);
    const userData = await api.me();
    setUser(userData);
  }

  async function logout(): Promise<void> {
    try {
      await api.logout();
    } finally {
      setToken(null);
      setUser(null);
    }
  }

  async function bootstrap(username: string, password: string): Promise<void> {
    const response = await api.bootstrap(username, password);
    setToken(response.access_token);
    setIsInitialized(true);
    const userData = await api.me();
    setUser(userData);
  }

  // Save return URL for redirect after login
  function saveReturnUrl(url: string): void {
    sessionStorage.setItem("auth_return_url", url);
  }

  function getReturnUrl(): string | null {
    const url = sessionStorage.getItem("auth_return_url");
    sessionStorage.removeItem("auth_return_url");
    return url;
  }

  return {
    user,
    token,
    loading,
    ready,
    authenticated,
    isInitialized,
    checkSetup,
    checkAuth,
    login,
    logout,
    bootstrap,
    saveReturnUrl,
    getReturnUrl,
  };
}

export const authStore = createRoot(createAuthStore);
