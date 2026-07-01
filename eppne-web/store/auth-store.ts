// store/auth-store.ts
import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { User } from "@/types/identity";

interface AuthState {
  // ✅ حالة المستخدم (في الذاكرة فقط - بدون persist)
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isInitialized: boolean; // ✅ معرفة ما إذا تم تهيئة المصادقة

  // ✅ الدوال
  setAuth: (user: User) => void;
  setLoading: (loading: boolean) => void;
  setInitialized: (initialized: boolean) => void;
  clearAuth: () => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  devtools(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: true,
      isInitialized: false,

      setAuth: (user) => {
        set({
          user,
          isAuthenticated: true,
          isLoading: false,
        });
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
          isAuthenticated: false,
          isLoading: false,
        });
      },

      logout: () => {
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
        });
      },
    }),
    { name: "auth-store" }
  )
);