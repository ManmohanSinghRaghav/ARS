import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authAPI } from '../api/client';

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Check token on mount
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      authAPI
        .me()
        .then((res) => setUser(res.data))
        .catch(() => {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (username: string, password: string) => {
    const res = await authAPI.login({ username, password });
    localStorage.setItem('access_token', res.data.access_token);
    localStorage.setItem('refresh_token', res.data.refresh_token);
    const meRes = await authAPI.me();
    setUser(meRes.data);
  };

  const register = async (username: string, email: string, password: string) => {
    await authAPI.register({ username, email, password });
    // Auto-login after register
    await login(username, password);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
