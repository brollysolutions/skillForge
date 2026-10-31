import { createContext, useContext, useEffect, useState } from 'react';
import { api, saveSession, clearSession, refreshSession } from '../api/client';
const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    const restore = async () => {
      try { await refreshSession(); const { data } = await api.get('/auth/profile/'); if (active) setUser(data); }
      catch { clearSession(); }
      finally { if (active) setLoading(false); }
    };
    restore();
    const expired = () => setUser(null);
    window.addEventListener('sf-session-expired', expired);
    return () => { active = false; window.removeEventListener('sf-session-expired', expired); };
  }, []);
  const login = async values => { const { data } = await api.post('/auth/login/', values); saveSession(data); setUser(data.user); };
  const logout = async () => {
    try { await api.post('/auth/logout/', { refresh: sessionStorage.getItem('sf-refresh') }); }
    finally { clearSession(); setUser(null); }
  };
  return <AuthContext.Provider value={{ user, loading, login, logout, setUser }}>{children}</AuthContext.Provider>;
}
