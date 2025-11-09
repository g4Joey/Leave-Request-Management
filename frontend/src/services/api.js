import axios from 'axios';

function resolveApiBaseUrl() {
  // Priority order:
  // 1. Explicit target override (REACT_APP_API_TARGET) – useful to force direct backend hitting bypassing proxy.
  // 2. Explicit full base URL (REACT_APP_API_URL) – production / remote DigitalOcean.
  // 3. Local dev proxy when on CRA dev server port (3000/3001) – relative '/api'.
  // 4. Fallback: same-origin '/api'.
  try {
    const target = process.env.REACT_APP_API_TARGET || process.env.REACT_APP_API_URL;
    if (target) {
      // Normalize: allow providing host without trailing /api
      if (/\/api\/?$/.test(target)) return target.replace(/\/$/, '');
      return target.replace(/\/$/, '') + '/api';
    }
    const { protocol, hostname, port } = window.location;
    const isLocal = ['localhost', '127.0.0.1'].includes(hostname);
    if (isLocal && (port === '3000' || port === '3001')) {
      return '/api';
    }
    const portPart = port ? `:${port}` : '';
    return `${protocol}//${hostname}${portPart}/api`;
  } catch (e) {
    return '/api';
  }
}

const API_URL = resolveApiBaseUrl();

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