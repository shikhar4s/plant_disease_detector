import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { api, ApiError, clearSession, saveTokens } from '../lib/api';
import type { User } from '../lib/types';

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
  authError: string;
  reloadUser: () => Promise<void>;
  updateProfile: (data: FormData | { full_name: string }) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState('');
  const reloadUser = useCallback(async () => {
    const profile = await api<User>('/api/users/me/');
    setUser(profile);
    setAuthError('');
  }, []);

  useEffect(() => {
    let active = true;
    const onLogout = () => { setUser(null); setAuthError(''); };
    window.addEventListener('plantdoc:logout', onLogout);
    if (!localStorage.getItem('access_token') && !localStorage.getItem('refresh_token')) {
      setIsLoading(false);
    } else {
      api<User>('/api/users/me/').then(profile => { if (active) setUser(profile); }).catch(error => {
        if (active && !(error instanceof ApiError && error.status === 401)) setAuthError('The server is unavailable. Try signing in again shortly.');
      }).finally(() => { if (active) setIsLoading(false); });
    }
    return () => { active = false; window.removeEventListener('plantdoc:logout', onLogout); };
  }, []);

  const authenticate = async (path: string, payload: object) => {
    setIsLoading(true);
    setAuthError('');
    try {
      const data = await api<{ access: string; refresh: string; user: User }>(path, {
        auth: false, method: 'POST', body: JSON.stringify(payload),
      });
      saveTokens(data.access, data.refresh);
      setUser(data.user);
    } finally { setIsLoading(false); }
  };
  const login = (email: string, password: string) => authenticate('/api/users/login/', { email, password });
  const signup = (email: string, password: string, name: string) =>
    authenticate('/api/users/register/', { email, password, confirm_password: password, full_name: name });
  const updateProfile = async (data: FormData | { full_name: string }) => {
    setUser(await api<User>('/api/users/me/', {
      method: 'PATCH', body: data instanceof FormData ? data : JSON.stringify(data),
    }));
  };
  return <AuthContext.Provider value={{ user, login, signup, logout: clearSession, isLoading,
    authError, reloadUser, updateProfile }}>{children}</AuthContext.Provider>;
}
