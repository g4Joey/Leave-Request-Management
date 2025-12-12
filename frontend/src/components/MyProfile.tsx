import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import api from '../services/api';
import { motion } from 'framer-motion';
import { User, Mail, Phone, Lock, Save, Briefcase, Hash, Calendar, Shield } from 'lucide-react';

function MyProfile() {
  const { user, setUser, refreshUser } = useAuth();
  const { showToast } = useToast();
  
  const [loading, setLoading] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [profileData, setProfileData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: ''
  });
  
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setProfileData(prev => ({ ...prev, [name]: value }));
  };

  useEffect(() => { refreshUser(); }, [refreshUser]);

  useEffect(() => {
    if (user) {
      setProfileData({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        email: user.email || '',
        phone: user.phone || ''
      });
    }
  }, [user]);

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordData(prev => ({ ...prev, [name]: value }));
  };

  const handleProfileUpdate = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      const updateData = {
        first_name: profileData.first_name,
        last_name: profileData.last_name,
        email: profileData.email,
        phone: profileData.phone
      };
      
      const response = await api.patch('/users/me/', updateData);
      
      setUser(prev => ({ 
        ...prev, 
        ...response.data
      }));
      showToast({ type: 'success', message: 'Profile updated successfully' });
    } catch (error) {
      console.error('Profile update error:', error);
      showToast({ type: 'error', message: error.response?.data?.detail || 'Failed to update profile' });
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordUpdate = async (e) => {
    e.preventDefault();
    
    if (passwordData.new_password !== passwordData.confirm_password) {
      showToast({ type: 'error', message: 'New passwords do not match' });
      return;
    }
    
    if (passwordData.new_password.length < 8) {
      showToast({ type: 'error', message: 'Password must be at least 8 characters long' });
      return;
    }

    try {
      setPasswordLoading(true);
      await api.post('/users/me/change-password/', {
        current_password: passwordData.current_password,
        new_password: passwordData.new_password
      });
      
      setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
      showToast({ type: 'success', message: 'Password changed successfully' });
    } catch (error) {
      console.error('Password change error:', error);
      showToast({ type: 'error', message: error.response?.data?.error || 'Failed to change password' });
    } finally {
      setPasswordLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 font-heading">My Profile</h1>
        <p className="text-gray-500 mt-1">Manage your personal information and security settings</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left Column - Main Profile Info */}
        <div className="lg:col-span-2 space-y-6">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white/80 backdrop-blur-md rounded-2xl shadow-sm border border-white/20 p-6"
          >
            <div className="flex items-center gap-2 mb-6 text-gray-900">
              <User className="w-5 h-5 text-primary" />
              <h2 className="text-lg font-semibold">Personal Information</h2>
            </div>

            <form onSubmit={handleProfileUpdate} className="space-y-6">
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">First Name</label>
                  <input
                    type="text"
                    name="first_name"
                    value={profileData.first_name}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Last Name</label>
                  <input
                    type="text"
                    name="last_name"
                    value={profileData.last_name}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                    required
                  />
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Email Address</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
                    <input
                      type="email"
                      name="email"
                      value={profileData.email}
                      onChange={handleInputChange}
                      className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                      required
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Phone Number</label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
                    <input
                      type="tel"
                      name="phone"
                      value={profileData.phone}
                      onChange={handleInputChange}
                      className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="flex items-center gap-2 px-6 py-2.5 bg-primary text-white rounded-lg font-medium hover:bg-primary-hover focus:ring-4 focus:ring-primary/10 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-primary/20"
                >
                  <Save className="w-4 h-4" />
                  {loading ? 'Saving Changes...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white/80 backdrop-blur-md rounded-2xl shadow-sm border border-white/20 p-6"
          >
            <div className="flex items-center gap-2 mb-6 text-gray-900">
              <Shield className="w-5 h-5 text-red-500" />
              <h2 className="text-lg font-semibold">Security</h2>
            </div>

            <form onSubmit={handlePasswordUpdate} className="space-y-4 max-w-lg">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Current Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
                  <input
                    type="password"
                    name="current_password"
                    value={passwordData.current_password}
                    onChange={handlePasswordChange}
                    className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500/20 focus:border-red-500 outline-none transition-all"
                    required
                  />
                </div>
              </div>
              
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">New Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
                    <input
                      type="password"
                      name="new_password"
                      value={passwordData.new_password}
                      onChange={handlePasswordChange}
                      className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500/20 focus:border-red-500 outline-none transition-all"
                      minLength={8}
                      required
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Confirm Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
                    <input
                      type="password"
                      name="confirm_password"
                      value={passwordData.confirm_password}
                      onChange={handlePasswordChange}
                      className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500/20 focus:border-red-500 outline-none transition-all"
                      required
                    />
                  </div>
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={passwordLoading}
                  className="px-6 py-2.5 bg-white border border-red-200 text-red-600 rounded-lg font-medium hover:bg-red-50 focus:ring-4 focus:ring-red-500/10 transition-all disabled:opacity-50"
                >
                  {passwordLoading ? 'Updating...' : 'Update Password'}
                </button>
              </div>
            </form>
          </motion.div>
        </div>

        {/* Right Column - Employment Details (Read-only) */}
        <div className="space-y-6">
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-primary text-white rounded-2xl shadow-lg p-6 relative overflow-hidden"
          >
            {/* Background Decoration */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full blur-2xl pointer-events-none transform translate-x-1/2 -translate-y-1/2"></div>
            
            <div className="flex items-center gap-4 mb-6 relative z-10">
              <div className="w-16 h-16 bg-white/20 backdrop-blur rounded-full flex items-center justify-center text-2xl font-bold font-heading">
                {user?.first_name?.[0]}{user?.last_name?.[0]}
              </div>
              <div>
                <h3 className="text-lg font-bold">{user?.first_name} {user?.last_name}</h3>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-accent text-white shadow-sm border border-white/20">
                  {user?.role?.replace('_', ' ')?.replace(/\b\w/g, l => l.toUpperCase()) || 'Staff'}
                </span>
              </div>
            </div>

            <div className="space-y-4 relative z-10">
              <div className="flex items-center gap-3 text-white/90">
                <Briefcase className="w-4 h-4 text-accent" />
                <span className="text-sm">{user?.department?.name || 'No Department'}</span>
              </div>
              <div className="flex items-center gap-3 text-white/90">
                <Hash className="w-4 h-4 text-accent" />
                <span className="text-sm">ID: {user?.employee_id || 'N/A'}</span>
              </div>
              <div className="flex items-center gap-3 text-white/90">
                <Calendar className="w-4 h-4 text-accent" />
                <span className="text-sm">{user?.annual_leave_entitlement || 0} Days Annual Leave</span>
              </div>
            </div>
          </motion.div>
          
          <div className="bg-white/60 backdrop-blur-sm rounded-xl p-4 text-xs text-gray-500 text-center">
             Contact HR to update employment details.
          </div>
        </div>
      </div>
    </div>
  );
}

export default MyProfile;