import { createContext, useContext, useEffect, useState } from "react";
import api, { setTokens, clearTokens, getAccessToken } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // No persisted token across reloads (in-memory only), so just finish loading.
    setLoading(false);
  }, []);

  async function login(username, password) {
    const { data } = await api.post("/auth/login/", { username, password });
    setTokens(data.access, data.refresh);
    const me = await api.get("/auth/me/");
    setUser(me.data);
    return me.data;
  }

  async function register(username, email, password) {
    await api.post("/auth/register/", { username, email, password });
    return login(username, password);
  }

  function logout() {
    clearTokens();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, isAuthed: !!getAccessToken() && !!user }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
