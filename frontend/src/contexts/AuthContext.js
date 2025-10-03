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
      const response = await api.post('/auth/token/', {
        username: email,
        password: password
      });
      
      const { access, refresh } = response.data;
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
            console.warn('AuthContext (login): Missing role in profile payload', profile);
        }
        setUser(normalized);
      } catch (e) {
        setUser({
          token: access,
          email,
          role: '',
          is_superuser: false,
          grade: null,
          grade_id: null,
          grade_slug: null,
        });
      }
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || 'Login failed' };
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