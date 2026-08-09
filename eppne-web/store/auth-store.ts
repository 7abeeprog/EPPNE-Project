// store/auth-store.ts
import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type { components } from "@/src/lib/api-types";

type User = components['schemas']['UserResponse'];

interface AuthState {
  user: User | null;
  // في الذاكرة فقط (لا localStorage) — يُستخدم حصريًا لمصافحة WebSocket في
  // دومين communications (لا يدعم كوكيز HttpOnly عبر نطاق wss:// الفرعي بسهولة).
  // لا يُستخدم إطلاقًا كـ Authorization header لأي طلب REST؛ الكوكي يكفي هناك.
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isInitialized: boolean;

  setUser: (user: User | null) => void;
  setAccessToken: (token: string | null) => void;
  setLoading: (loading: boolean) => void;
  setInitialized: (initialized: boolean) => void;
  clearAuth: () => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  devtools(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: true,
      isInitialized: false,

      setUser: (user) => {
        set({ user, isAuthenticated: !!user, isLoading: false });
      },

      setAccessToken: (token) => {
        set({ accessToken: token });
      },

      setLoading: (isLoading) => {
        set({ isLoading });
      },

      setInitialized: (isInitialized) => {
        set({ isInitialized });
      },

      clearAuth: () => {
        set({
          user: null,
          accessToken: null,
          isAuthenticated: false,
          isLoading: false,
        });
      },

      logout: () => {
        set({
          user: null,
          accessToken: null,
          isAuthenticated: false,
          isLoading: false,
        });
      },
    }),
    { name: "auth-store" }
  )
);