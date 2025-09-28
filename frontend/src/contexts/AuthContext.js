import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

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
          const profileRes = await api.get('/users/me/');
          const profile = profileRes.data || {};
          
          // Debug profile data
          console.log('🔍 DEBUG - Profile data from /users/me/:', profile);
          
          const userData = {
            token,
            email: profile.email,
            first_name: profile.first_name,
            last_name: profile.last_name,
            role: profile.role,
            is_superuser: profile.is_superuser,
            employee_id: profile.employee_id,
            department: profile.department,
            annual_leave_entitlement: profile.annual_leave_entitlement,
            phone: profile.phone,
            profile_image: profile.profile_image
          };
          
          console.log('🔍 DEBUG - Processed user data:', userData);
          setUser(userData);
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
        
        console.log('🔍 DEBUG - Login profile data:', profile);
        
        const userData = {
          token: access,
          email: profile.email || email,
          first_name: profile.first_name,
          last_name: profile.last_name,
          role: profile.role,
          is_superuser: profile.is_superuser,
          employee_id: profile.employee_id,
          department: profile.department,
          annual_leave_entitlement: profile.annual_leave_entitlement,
          phone: profile.phone,
          profile_image: profile.profile_image
        };
        
        console.log('🔍 DEBUG - Login user data:', userData);
        setUser(userData);
      } catch (e) {
        setUser({ token: access, email });
      }
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || 'Login failed' };
    }
  };

  const logout = () => {
    console.log('🔍 DEBUG - Logout called');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };  const value = { user, setUser, login, logout, loading };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
}