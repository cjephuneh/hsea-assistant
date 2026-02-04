import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import { api } from './api';
import type { User } from './api';

type AuthContextType = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  register: (name: string, email: string, password: string, phone?: string) => Promise<boolean>;
  logout: () => void;
};

const defaultAuthContext: AuthContextType = {
  user: null,
  loading: true,
  login: async () => false,
  register: async () => false,
  logout: () => {},
};

const AuthContext = createContext<AuthContextType>(defaultAuthContext);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    api.auth.me().then(({ data, status }) => {
      if (status === 200) {
        setUser(data as User);
      } else {
        // 401 or 422 - invalid token, clear it immediately
        localStorage.removeItem('access_token');
        setUser(null);
      }
      setLoading(false);
    }).catch(() => {
      localStorage.removeItem('access_token');
      setUser(null);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    const onSessionInvalid = () => {
      localStorage.removeItem('access_token');
      setUser(null);
    };
    window.addEventListener('auth:session-invalid', onSessionInvalid);
    return () => window.removeEventListener('auth:session-invalid', onSessionInvalid);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    try {
      const { data, status } = await api.auth.login(email, password);
      if (status === 200 && data && 'access_token' in data) {
        const token = (data as { access_token: string }).access_token;
        // Ensure token is stored correctly without extra whitespace
        localStorage.setItem('access_token', token.trim());
        setUser((data as { user: User }).user);
        return true;
      }
      console.error('Login failed:', status, data);
      return false;
    } catch (error) {
      console.error('Login error:', error);
      return false;
    }
  }, []);

  const register = useCallback(async (name: string, email: string, password: string, phone?: string) => {
    try {
      const { data, status } = await api.auth.register(name, email, password, phone);
      if (status === 201 && data && 'access_token' in data) {
        localStorage.setItem('access_token', (data as { access_token: string }).access_token);
        setUser((data as { user: User }).user);
        return true;
      }
      // Store error message for display
      const errorMsg = (data as { error?: string })?.error || 'Registration failed';
      console.error('Registration failed:', status, errorMsg);
      return false;
    } catch (error) {
      console.error('Registration error:', error);
      return false;
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('access_token');
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
