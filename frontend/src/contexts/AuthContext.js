import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
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
    affiliate: profile.affiliate || null,
    affiliate_name: profile.affiliate?.name || null,
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
  const [showTimeoutWarning, setShowTimeoutWarning] = useState(false);
  const isWarningActive = useRef(false);
  const warningTimer = useRef(null);
  const logoutTimer = useRef(null);

  // Initialize auth state on mount: load token, fetch profile, then clear loading
  useEffect(() => {
    let cancelled = false;
    const init = async () => {
      try {
        const token = localStorage.getItem('token');
        if (token) {
          api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          try {
            const response = await api.get('/users/me/');
            if (cancelled) return;
            const profile = response.data || {};
            const normalized = normalizeProfile(profile, token);
            if (!normalized.role) {
              console.warn('AuthContext: Missing role in profile payload', profile);
            }
            setUser(normalized);
          } catch (e) {
            // Token might be invalid; clear it and proceed unauthenticated
            localStorage.removeItem('token');
            localStorage.removeItem('refresh_token');
            delete api.defaults.headers.common['Authorization'];
            setUser(null);
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    init();
    return () => { cancelled = true; };
  }, []);

  const hardLogout = () => {
    try {
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
      delete api.defaults.headers.common['Authorization'];
    } catch (_) {}
    setUser(null);
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  };

  const clearAllTimers = React.useCallback(() => {
    if (warningTimer.current) clearTimeout(warningTimer.current);
    if (logoutTimer.current) clearTimeout(logoutTimer.current);
  }, []);

  const startTimers = React.useCallback(() => {
    clearAllTimers();
    setShowTimeoutWarning(false);
    isWarningActive.current = false;

    warningTimer.current = setTimeout(() => {
      setShowTimeoutWarning(true);
      isWarningActive.current = true;
      logoutTimer.current = setTimeout(() => {
        hardLogout();
      }, 2 * 60 * 1000); // 2 minutes
    }, 10 * 60 * 1000); // 10 minutes
  }, [clearAllTimers]);

  const onActivity = React.useCallback(() => {
    if (!isWarningActive.current) {
      startTimers();
    }
  }, [startTimers]);

  useEffect(() => {
    if (!user) return;

    const activityEvents = ['mousemove', 'keydown', 'click', 'touchstart', 'wheel', 'scroll'];
    activityEvents.forEach((evt) => window.addEventListener(evt, onActivity, { passive: true }));
    startTimers();

    return () => {
      clearAllTimers();
      activityEvents.forEach((evt) => window.removeEventListener(evt, onActivity));
    };
  }, [user, onActivity, startTimers, clearAllTimers]);

  const keepSessionActive = () => {
    startTimers();
  };

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
      {!loading && (
        <>
          {children}
          {showTimeoutWarning && (
            <div className="fixed inset-0 z-50 flex items-center justify-center">
              <div className="absolute inset-0 bg-black bg-opacity-40" />
              <div className="relative bg-white rounded-lg shadow-xl p-6 w-full max-w-sm text-center">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Session Inactivity</h3>
                <p className="text-sm text-gray-700 mb-4">Your session will timeout in 2 minutes.</p>
                <button
                  onClick={keepSessionActive}
                  className="inline-flex justify-center rounded-md bg-primary-600 text-white px-4 py-2 text-sm font-medium hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                >
                  Keep My Session Active
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </AuthContext.Provider>
  );
}