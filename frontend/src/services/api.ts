import axios from 'axios';
import { MOCK_USER, MOCK_LEAVE_TYPES, MOCK_LEAVE_REQUESTS, MOCK_STATS } from './mockData';

function resolveApiBaseUrl() {
  const fromEnv = import.meta.env.VITE_API_URL;
  if (fromEnv) return fromEnv;
  return 'http://localhost:8000';
}

const api = axios.create({
  baseURL: resolveApiBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
});

// Mock Adapter Logic
// Change this to false to connect to real backend
const USE_MOCK = true;

if (USE_MOCK) {
  console.log('🔶 MOCK MODE ENABLED: Backend calls are intercepted.');
  
  // Custom adapter to intercept requests
  api.interceptors.request.use(async (config) => {
    // Only intercept if it's not a refresh token call (optional, but robust)
    config.adapter = async (cfg) => {
      const { url, method } = cfg;
      console.log(`[Mock API] ${method?.toUpperCase()} ${url}`);

      return new Promise((resolve) => {
        setTimeout(() => {
          let data: any = {};
          let status = 200;

          if (url?.includes('/auth/token/refresh/')) { // Handle refresh
            data = { access: 'mock-new-access-token' };
          }
          else if (url?.includes('/auth/token/')) {
            data = { access: 'mock-access-token', refresh: 'mock-refresh-token' };
          } else if (url?.includes('/users/me/')) {
            data = MOCK_USER;
          } else if (url?.includes('/leaves/types/')) {
            data = MOCK_LEAVE_TYPES;
          } else if (url?.includes('/leaves/requests/') && method === 'get') {
            data = { results: MOCK_LEAVE_REQUESTS };
          } else if (url?.includes('/leaves/requests/') && method === 'post') {
            data = { detail: 'Mock Request Submitted' };
            status = 201;
          } else if (url?.includes('/dashboard/stats/') || url?.includes('stats')) {
             data = MOCK_STATS;
          } else if (url?.includes('/leaves/overlaps/')) {
            data = { overlaps: [] };
          }

          resolve({
            data,
            status,
            statusText: 'OK',
            headers: {},
            config: cfg,
          });
        }, 300);
      });
    };
    return config;
  });
}

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

    // Use baseURL for refresh call
    const baseURL = resolveApiBaseUrl();

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${baseURL}/auth/token/refresh/`, {
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