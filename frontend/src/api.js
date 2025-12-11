import axios from 'axios';

// CRA exposes env vars prefixed with REACT_APP_
const API_BASE = process.env.REACT_APP_API_BASE || 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: API_BASE,
});

export async function login(email, password) {
  const res = await api.post('/api/auth/token/', { username: email, password });
  return res.data;
}

export async function getProfile(token) {
  const res = await api.get('/api/users/me/', {
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.data;
}

export default api;
