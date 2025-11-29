import axios from 'axios';

function resolveApiBaseUrl() {
  // Prefer explicit env var when provided (build-time)
  const fromEnv = process.env.REACT_APP_API_URL;
  if (fromEnv) return fromEnv;

  // Fallback: use current host (so it works over LAN/IP) but port 8000 for Django
  try {
    const { protocol, hostname } = window.location;
    const port = window.location.port;
    // In production (unified Docker) Django lives on the same origin.
    // Use same-origin /api.
    const portPart = port ? `:${port}` : '';
    return `${protocol}//${hostname}${portPart}/api`;
  } catch (e) {
    // SSR or unexpected context: default to localhost
    return 'http://localhost:8000/api';
  }
}

const API_URL = resolveApiBaseUrl();

// Helpful runtime visibility for debugging login/base URL issues in dev
if (typeof window !== 'undefined') {
  // Only log once per load
  if (!window.__API_BASE_LOGGED) {
    console.info('[API] Base URL resolved to:', API_URL);
    window.__API_BASE_LOGGED = true;
  }
}

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_URL}/auth/token/refresh/`, {
            refresh: refreshToken,
          });

          const { access } = response.data;
          localStorage.setItem('token', access);
          api.defaults.headers.common['Authorization'] = `Bearer ${access}`;

          return api(originalRequest);
        }
      } catch (refreshError) {
        localStorage.removeItem('token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

export default api;