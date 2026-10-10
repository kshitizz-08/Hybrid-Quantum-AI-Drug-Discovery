/**
 * Zustand auth store — manages JWT token and current user session.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '../types';
import { authApi } from '../api/client';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; username: string; password: string; full_name?: string }) => Promise<void>;
  logout: () => void;
  clearError: () => void;
  fetchMe: () => Promise<void>;
}

function extractErrorMessage(err: unknown, fallback: string): string {
  const e = err as {
    code?: string;
    message?: string;
    response?: { data?: { detail?: string | Array<{ msg?: string }> } };
  };
  if (!e?.response) {
    if (e?.code === 'ERR_NETWORK' || e?.message?.includes('Network Error')) {
      return 'Cannot connect to backend server. Please make sure the backend is running at http://localhost:8000.';
    }
    return e?.message || fallback;
  }
  const detail = e.response.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join('. ');
  }
  return fallback;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email, password) => {
        set({ isLoading: true, error: null });
        try {
          const res = await authApi.login({ email, password });
          const { access_token, user } = res.data;
          localStorage.setItem('access_token', access_token);
          set({ token: access_token, user, isAuthenticated: true, isLoading: false });
        } catch (err: unknown) {
          const message = extractErrorMessage(err, 'Login failed. Please check your credentials.');
          set({ error: message, isLoading: false });
          throw err;
        }
      },

      register: async (data) => {
        set({ isLoading: true, error: null });
        try {
          const res = await authApi.register(data);
          const { access_token, user } = res.data;
          localStorage.setItem('access_token', access_token);
          set({ token: access_token, user, isAuthenticated: true, isLoading: false });
        } catch (err: unknown) {
          const message = extractErrorMessage(err, 'Registration failed. Please try again.');
          set({ error: message, isLoading: false });
          throw err;
        }
      },

      logout: () => {
        localStorage.removeItem('access_token');
        set({ user: null, token: null, isAuthenticated: false, error: null });
      },

      clearError: () => set({ error: null }),

      fetchMe: async () => {
        const { token } = get();
        if (!token) return;
        try {
          const res = await authApi.me();
          set({ user: res.data, isAuthenticated: true });
        } catch {
          get().logout();
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ token: state.token, user: state.user }),
    }
  )
);
