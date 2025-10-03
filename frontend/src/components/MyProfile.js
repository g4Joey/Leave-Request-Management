import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import api from '../services/api';

function MyProfile() {
  const { user, setUser, refreshUser } = useAuth();
  const { showToast } = useToast();
  const fileInputRef = useRef(null);
  const canvasRef = useRef(null);
  
  const [loading, setLoading] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [profileData, setProfileData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    profile_image: null
  });
  
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  
  const [imageUpload, setImageUpload] = useState({
    file: null,
    preview: null,
    cropping: false,
    cropData: { x: 0, y: 0, width: 160, height: 160 }
  });

  // Refresh user data when component loads
  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  // Load user profile data
  useEffect(() => {
    if (user) {
      console.log('👤 User object updated:', user);
      console.log('👤 Profile image value:', user.profile_image);
      setProfileData({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        email: user.email || '',
        phone: user.phone || '',
        profile_image: user.profile_image || null
      });
    }
  }, [user]);

  // Helper function to get full image URL
  const getImageUrl = (imagePath) => {
    console.log('🖼️ getImageUrl called with:', imagePath);
    if (!imagePath) {
      console.log('🖼️ No image path provided');
      return null;
    }
    if (imagePath.startsWith('http')) {
      console.log('🖼️ Full URL detected:', imagePath);
      return imagePath;
    }
    // Get the base API URL and remove '/api' suffix if present
    const baseUrl = api.defaults.baseURL.replace('/api', '');
    const fullUrl = `${baseUrl}${imagePath.startsWith('/') ? imagePath : '/' + imagePath}`;
    console.log('🖼️ Constructed URL:', fullUrl);
    console.log('🖼️ API baseURL:', api.defaults.baseURL);
    console.log('🖼️ Base URL:', baseUrl);
    return fullUrl;
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setProfileData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleImageSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        showToast('Please select an image file', 'error');
        return;
      }
      
      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        showToast('Image size must be less than 5MB', 'error');
        return;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        setImageUpload({
          file,
          preview: e.target.result,
          cropping: true,
          cropData: { x: 0, y: 0, width: 160, height: 160 }
        });
      };
      reader.readAsDataURL(file);
    }
  };

  const handleImageCrop = () => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const img = new Image();
    
    img.onload = () => {
      canvas.width = 160;
      canvas.height = 160;
      
      const { x, y, width, height } = imageUpload.cropData;
      ctx.drawImage(img, x, y, width, height, 0, 0, 160, 160);
      
      canvas.toBlob(async (blob) => {
        if (!blob) {
          console.error('❌ Failed to create image blob from canvas');
          showToast('Failed to process image before upload', 'error');
          return;
        }

        console.log('📤 Uploading image blob:', blob);
        console.log('📤 Blob size:', blob.size);
        console.log('📤 Blob type:', blob.type);

        const formData = new FormData();
        formData.append('profile_image', blob, 'profile_image.jpg');

        try {
          setLoading(true);
          const response = await api.patch('/users/me/', formData);
          console.log('📥 Image upload response:', response.data);
          if (!response.data.profile_image) {
            console.warn('⚠️ Response missing profile_image field');
          }
          setUser(prev => ({ ...prev, profile_image: response.data.profile_image }));
          setImageUpload({ file: null, preview: null, cropping: false, cropData: { x: 0, y: 0, width: 160, height: 160 } });
          showToast('Profile image updated successfully', 'success');
        } catch (error) {
          console.error('Image upload error:', error);
          console.error('Image upload error response:', error.response?.data);
          showToast(error.response?.data?.detail || error.response?.data?.profile_image?.[0] || 'Failed to update profile image', 'error');
        } finally {
          setLoading(false);
        }
      }, 'image/jpeg', 0.9);
    };
    
    img.src = imageUpload.preview;
  };

  const handleProfileUpdate = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      // Exclude profile_image from JSON updates - it should only be updated via multipart uploads
      const updateData = {
        first_name: profileData.first_name,
        last_name: profileData.last_name,
        email: profileData.email,
        phone: profileData.phone
      };
      console.log('Sending profile data:', updateData);
      const response = await api.patch('/users/me/', updateData);
      console.log('Profile update response:', response.data);
      setUser(prev => ({ 
        ...prev, 
        first_name: response.data.first_name,
        last_name: response.data.last_name,
        email: response.data.email,
        phone: response.data.phone,
        grade: response.data.grade ?? prev?.grade ?? null,
        grade_id: response.data.grade?.id ?? response.data.grade_id ?? prev?.grade_id ?? null,
        grade_slug: response.data.grade?.slug ?? prev?.grade_slug ?? null,
      }));
      showToast('Profile updated successfully', 'success');
    } catch (error) {
      console.error('Profile update error:', error);
      console.error('Error response:', error.response?.data);
      console.error('Error status:', error.response?.status);
      showToast(error.response?.data?.detail || error.response?.data?.message || 'Failed to update profile', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordUpdate = async (e) => {
    e.preventDefault();
    
    if (passwordData.new_password !== passwordData.confirm_password) {
      showToast('New passwords do not match', 'error');
      return;
    }
    
    if (passwordData.new_password.length < 8) {
      showToast('Password must be at least 8 characters long', 'error');
      return;
    }

    try {
      setPasswordLoading(true);
      await api.post('/users/me/change-password/', {
        current_password: passwordData.current_password,
        new_password: passwordData.new_password
      });
      
      setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
      showToast('Password changed successfully', 'success');
    } catch (error) {
      console.error('Password change error:', error);
      showToast(error.response?.data?.error || 'Failed to change password', 'error');
    } finally {
      setPasswordLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h1 className="text-2xl font-bold text-gray-900">My Profile</h1>
          <p className="text-gray-600">Manage your personal information and preferences</p>
          <div className="mt-2 inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 text-blue-800 text-sm font-medium">
            <span>Your grade:</span>
            <span>{user?.grade?.name || 'Not assigned'}</span>
          </div>
        </div>

        <div className="p-6 space-y-8">
          {/* Profile Image Section */}
          <div className="flex items-start space-x-6">
            <div className="flex-shrink-0">
              <div className="relative">
                <div className="w-32 h-32 bg-gray-200 rounded-full overflow-hidden border-4 border-white shadow-lg">
                  {user?.profile_image ? (
                    <>
                      <img 
                        src={getImageUrl(user.profile_image)} 
                        alt="Profile" 
                        className="w-full h-full object-cover"
                        onLoad={(e) => {
                          console.log('✅ Image loaded successfully:', e.target.src);
                        }}
                        onError={(e) => {
                          console.log('❌ Image load error for path:', user.profile_image);
                          console.log('❌ Image load error for URL:', e.target.src);
                          console.log('❌ Image error event:', e);
                          e.target.style.display = 'none';
                          e.target.nextSibling.style.display = 'flex';
                        }}
                      />
                      <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-blue-400 to-blue-600" style={{display: 'none'}}>
                        <span className="text-2xl font-bold text-white">
                          {user?.first_name?.[0]}{user?.last_name?.[0]}
                        </span>
                      </div>
                    </>
                  ) : (
                    <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-blue-400 to-blue-600">
                      <span className="text-2xl font-bold text-white">
                        {user?.first_name?.[0]}{user?.last_name?.[0]}
                      </span>
                    </div>
                  )}
                </div>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="absolute bottom-0 right-0 bg-blue-600 text-white p-2 rounded-full shadow-lg hover:bg-blue-700 transition-colors"
                  disabled={loading}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-medium text-gray-900">Profile Picture</h3>
              <p className="text-sm text-gray-600 mb-3">
                Upload a new profile picture. Images will be cropped to 160x160 pixels.
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleImageSelect}
                className="hidden"
              />
              {user?.profile_image && (
                <button
                  onClick={() => {
                    const formData = new FormData();
                    formData.append('profile_image', '');
                    api.patch('/users/me/', formData).then(() => {
                      setUser(prev => ({ ...prev, profile_image: null }));
                      showToast('Profile image removed', 'success');
                    });
                  }}
                  className="text-sm text-red-600 hover:text-red-800"
                >
                  Remove image
                </button>
              )}
            </div>
          </div>

          {/* Image Cropping Modal */}
          {imageUpload.cropping && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
                <h3 className="text-lg font-semibold mb-4">Crop Image</h3>
                <div className="mb-4">
                  <img 
                    src={imageUpload.preview} 
                    alt="Preview" 
                    className="max-w-full h-auto border border-gray-300 rounded"
                  />
                </div>
                <canvas ref={canvasRef} className="hidden" />
                <div className="flex justify-end space-x-3">
                  <button
                    onClick={() => setImageUpload({ file: null, preview: null, cropping: false, cropData: { x: 0, y: 0, width: 160, height: 160 } })}
                    className="px-4 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleImageCrop}
                    disabled={loading}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                  >
                    {loading ? 'Uploading...' : 'Save Image'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Profile Information Form */}
          <form onSubmit={handleProfileUpdate} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  First Name
                </label>
                <input
                  type="text"
                  name="first_name"
                  value={profileData.first_name}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Last Name
                </label>
                <input
                  type="text"
                  name="last_name"
                  value={profileData.last_name}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email
                </label>
                <input
                  type="email"
                  name="email"
                  value={profileData.email}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Phone
                </label>
                <input
                  type="tel"
                  name="phone"
                  value={profileData.phone}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Read-only fields */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-gray-200">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Employee ID
                </label>
                <input
                  type="text"
                  value={user?.employee_id || ''}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                  disabled
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Role
                </label>
                <div className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    user?.role === 'junior_staff' ? 'bg-gray-100 text-gray-800' :
                    user?.role === 'senior_staff' ? 'bg-slate-100 text-slate-800' :
                    user?.role === 'manager' ? 'bg-blue-100 text-blue-800' :
                    user?.role === 'hr' ? 'bg-green-100 text-green-800' :
                    user?.role === 'admin' ? 'bg-purple-100 text-purple-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {user?.role?.replace('_', ' ')?.replace(/\b\w/g, l => l.toUpperCase()) || 'Staff'}
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Employment Grade
                </label>
                <input
                  type="text"
                  value={user?.grade?.name || 'Not assigned'}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                  disabled
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Department
                </label>
                <input
                  type="text"
                  value={user?.department?.name || 'Not assigned'}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                  disabled
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Annual Leave Entitlement
                </label>
                <input
                  type="text"
                  value={`${user?.annual_leave_entitlement || 0} days`}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                  disabled
                />
              </div>
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Updating...' : 'Update Profile'}
              </button>
            </div>
          </form>

          {/* Password Change Form */}
          <div className="pt-8 border-t border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Change Password</h3>
            <form onSubmit={handlePasswordUpdate} className="space-y-4 max-w-md">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Current Password
                </label>
                <input
                  type="password"
                  name="current_password"
                  value={passwordData.current_password}
                  onChange={handlePasswordChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  New Password
                </label>
                <input
                  type="password"
                  name="new_password"
                  value={passwordData.new_password}
                  onChange={handlePasswordChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  minLength={8}
                  required
                />
                <p className="text-xs text-gray-500 mt-1">Minimum 8 characters</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Confirm New Password
                </label>
                <input
                  type="password"
                  name="confirm_password"
                  value={passwordData.confirm_password}
                  onChange={handlePasswordChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              
              <button
                type="submit"
                disabled={passwordLoading}
                className="px-6 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {passwordLoading ? 'Changing...' : 'Change Password'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default MyProfile;