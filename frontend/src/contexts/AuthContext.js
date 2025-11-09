import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

const normalizeProfile = (profile = {}, token = null) => {
  const grade = profile.grade ?? null;
  const gradeId = grade?.id ?? profile.grade_id ?? null;
  const gradeSlug = grade?.slug ?? profile.grade_slug ?? null;
  return {
    token,
    email: profile.email,
    first_name: profile.first_name,
    last_name: profile.last_name,
    role: (profile.role || '').toLowerCase(),
    role_display: profile.role_display,
    is_superuser:
      profile.is_superuser === true ||
      profile.is_superuser === 'true' ||
      profile.is_superuser === 'True',
    employee_id: profile.employee_id,
    department: profile.department,
    annual_leave_entitlement: profile.annual_leave_entitlement,
    phone: profile.phone,
    profile_image: profile.profile_image,
    grade,
    grade_id: gradeId,
    grade_slug: gradeSlug,
  };
};

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const init = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        try {
          const response = await api.get('/users/me/');
          const profile = response.data || {};
          const normalized = normalizeProfile(profile, token);
          // Defensive logging if role missing or unexpected
          if (!normalized.role) {
            console.warn('AuthContext: Missing role in profile payload', profile);
          }
          setUser(normalized);
        } catch (e) {
          // token might be invalid; clear it
          localStorage.removeItem('token');
          localStorage.removeItem('refresh_token');
          delete api.defaults.headers.common['Authorization'];
          setUser(null);
        }
      }
      setLoading(false);
    };
    init();
  }, []);

  const login = async (email, password) => {
    try {
      // Clear any stale tokens before attempting a new login
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
      delete api.defaults.headers.common['Authorization'];

      const response = await api.post('/auth/token/', {
        // Send both username and email for maximum compatibility with backends
        username: email,
        email: email,
        password: password,
      });
      // Validate expected token fields
      const raw = response?.data;
      const access = raw?.access || raw?.data?.access || raw?.token || raw?.data?.token;
      const refresh = raw?.refresh || raw?.data?.refresh;
      if (!access || !refresh || typeof access !== 'string' || typeof refresh !== 'string') {
        // Helpful debug in dev without exposing secrets
        if (process.env.NODE_ENV !== 'production') {
          // eslint-disable-next-line no-console
          console.error('Login: Unexpected token payload', { status: response?.status, dataType: typeof raw, keys: raw && Object.keys(raw) });
        }
        // Fallback: try form-encoded submission in case backend expects it
        try {
          const form = new URLSearchParams();
          form.append('username', email);
          form.append('email', email);
          form.append('password', password);
          const resp2 = await api.post('/auth/token/', form, {
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
              'Accept': 'application/json',
            },
          });
          const raw2 = resp2?.data;
          const access2 = raw2?.access || raw2?.data?.access || raw2?.token || raw2?.data?.token;
          const refresh2 = raw2?.refresh || raw2?.data?.refresh;
          if (!access2 || !refresh2 || typeof access2 !== 'string' || typeof refresh2 !== 'string') {
            if (process.env.NODE_ENV !== 'production') {
              // eslint-disable-next-line no-console
              console.error('Login (fallback) still unexpected payload', { status: resp2?.status, dataType: typeof raw2, keys: raw2 && Object.keys(raw2) });
            }
            return { success: false, error: 'Invalid login response from server' };
          }
          localStorage.setItem('token', access2);
          localStorage.setItem('refresh_token', refresh2);
          api.defaults.headers.common['Authorization'] = `Bearer ${access2}`;
        } catch (fallbackErr) {
          return { success: false, error: 'Invalid login response from server' };
        }
      }
      localStorage.setItem('token', access);
      localStorage.setItem('refresh_token', refresh);
      api.defaults.headers.common['Authorization'] = `Bearer ${access}`;
      // Fetch profile after login to greet by name
      try {
        const profileRes = await api.get('/users/me/');
        const profile = profileRes.data || {};
        const normalized = normalizeProfile({
          ...profile,
          email: profile.email || email,
        }, access);
        if (!normalized.role) {
          // If role missing, treat as login failure to avoid landing in a generic, under-privileged UI
          localStorage.removeItem('token');
          localStorage.removeItem('refresh_token');
          delete api.defaults.headers.common['Authorization'];
          return { success: false, error: 'Profile did not include role. Please try again or contact support.' };
        }
        setUser(normalized);
      } catch (e) {
        // If profile fetch fails, treat login as failed to prevent entering app without role-based features
        localStorage.removeItem('token');
        localStorage.removeItem('refresh_token');
        delete api.defaults.headers.common['Authorization'];
        return { success: false, error: 'Failed to load profile after login' };
      }
      return { success: true };
    } catch (error) {
      // Prefer detailed API error messages when available
      const data = error.response?.data;
      const detail = (typeof data?.detail === 'string' && data.detail)
        || (Array.isArray(data?.non_field_errors) && data.non_field_errors.join(' '))
        || (typeof data?.error === 'string' && data.error)
        || null;
      return { success: false, error: detail || 'Login failed' };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  const refreshUser = async () => {
    const token = localStorage.getItem('token');
    if (token && user) {
      try {
        const response = await api.get('/users/me/');
        const profile = response.data || {};
        const normalized = normalizeProfile(profile, token);
        setUser(normalized);
        console.log('🔄 User profile refreshed:', normalized);
        return normalized;
      } catch (e) {
        console.error('Failed to refresh user profile:', e);
      }
    }
    return user;
  };

  const value = { user, setUser, login, logout, refreshUser, loading };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
}