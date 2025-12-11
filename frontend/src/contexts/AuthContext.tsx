import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import api from '../services/api';

export interface User {
  id: number;
  token?: string | null;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  role_display?: string;
  is_superuser: boolean;
  employee_id?: string;
  department?: {
    id: number;
    name: string;
  } | null;
  affiliate?: {
    id: number;
    name: string;
  } | null;
  affiliate_name?: string | null;
  annual_leave_entitlement?: number;
  phone?: string;
  profile_image?: string;
  grade?: any;
  grade_id?: number | null;
  grade_slug?: string | null;
}

interface AuthContextType {
  user: User | null;
  setUser: React.Dispatch<React.SetStateAction<User | null>>;
  loading: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  refreshUser: () => Promise<User | null | undefined>;
}

const normalizeProfile = (profile: any = {}, token: string | null = null): User => {
  const grade = profile.grade ?? null;
  const gradeId = grade?.id ?? profile.grade_id ?? null;
  const gradeSlug = grade?.slug ?? profile.grade_slug ?? null;
  return {
    id: profile.id, // Ensure ID is captured
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

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
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

  const login = async (email: string, password: string) => {
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
          id: 0, // Fallback ID
          token: access,
          email,
          first_name: '',
          last_name: '',
          role: '',
          is_superuser: false,
          grade: null,
          grade_id: null,
          grade_slug: null,
        });
      }
      return { success: true };
    } catch (error: any) {
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