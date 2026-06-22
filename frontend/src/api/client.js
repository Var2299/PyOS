import axios from "axios";

// In-memory token store for the session.
let accessToken = null;
let refreshToken = null;

export function setTokens(access, refresh) {
  accessToken = access;
  if (refresh !== undefined) refreshToken = refresh;
}
export function clearTokens() {
  accessToken = null;
  refreshToken = null;
}
export function getAccessToken() {
  return accessToken;
}

const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && refreshToken && !original._retried) {
      original._retried = true;
      try {
        const { data } = await axios.post("/api/auth/refresh/", { refresh: refreshToken });
        setTokens(data.access);
        original.headers.Authorization = `Bearer ${data.access}`;
        return api(original);
      } catch (e) {
        clearTokens();
      }
    }
    return Promise.reject(error);
  }
);

export default api;
