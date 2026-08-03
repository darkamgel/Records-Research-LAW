"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, setToken, setWorkspace, getToken } from "./api";
import type { CurrentUser } from "@/types";

interface AuthState {
  user: CurrentUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string, ws: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  async function refresh() {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await apiFetch<CurrentUser>("/auth/me");
      setUser(me);
      if (me.active_workspace_id) setWorkspace(me.active_workspace_id);
    } catch {
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function login(email: string, password: string) {
    const res = await apiFetch<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: { email, password },
    });
    setToken(res.access_token);
    await refresh();
    router.push("/dashboard");
  }

  async function register(email: string, password: string, fullName: string, ws: string) {
    const res = await apiFetch<{ access_token: string }>("/auth/register", {
      method: "POST",
      body: { email, password, full_name: fullName, workspace_name: ws },
    });
    setToken(res.access_token);
    await refresh();
    router.push("/dashboard");
  }

  function logout() {
    apiFetch("/auth/logout", { method: "POST" }).catch(() => {});
    setToken(null);
    setWorkspace(null);
    setUser(null);
    router.push("/login");
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
