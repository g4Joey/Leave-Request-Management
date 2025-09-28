import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Link, useLocation } from 'react-router-dom';

function Navbar() {
  const { logout, user } = useAuth();
  const location = useLocation();

  const isActive = (path) => location.pathname === path;
  
  // Debug user data in console (for production debugging)
  React.useEffect(() => {
    if (user) {
      console.log('🔍 DEBUG - User data in Navbar:', {
        role: user.role,
        is_superuser: user.is_superuser,
        email: user.email,
        first_name: user.first_name,
        should_see_manager: user?.role === 'manager' || user?.is_superuser,
        should_see_staff: user?.role === 'hr' || user?.is_superuser,
      });
    }
  }, [user]);

  return (
    <nav className="bg-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <h1 className="text-xl font-bold text-gray-800">
                Leave Management
              </h1>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              <Link
                to="/dashboard"
                className={`${
                  isActive('/dashboard') || isActive('/')
                    ? 'border-primary-500 text-gray-900'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
              >
                Dashboard
              </Link>
              <Link
                to="/request"
                className={`${
                  isActive('/request')
                    ? 'border-primary-500 text-gray-900'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
              >
                Request Leave
              </Link>
              <Link
                to="/history"
                className={`${
                  isActive('/history')
                    ? 'border-primary-500 text-gray-900'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
              >
                Leave History
              </Link>
              <Link
                to="/profile"
                className={`${
                  isActive('/profile')
                    ? 'border-primary-500 text-gray-900'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
              >
                My Profile
              </Link>
              {(() => {
                const canSeeManager = user && (user.role === 'manager' || user.is_superuser === true);
                return canSeeManager && (
                  <Link
                    to="/manager"
                    className={`${
                      isActive('/manager')
                        ? 'border-primary-500 text-gray-900'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
                  >
                    Manager
                  </Link>
                );
              })()}
              {(() => {
                const canSeeStaff = user && (user.role === 'hr' || user.is_superuser === true);
                return canSeeStaff && (
                  <Link
                    to="/staff"
                    className={`${
                      isActive('/staff')
                        ? 'border-primary-500 text-gray-900'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
                  >
                    Staff
                  </Link>
                );
              })()}
            </div>
          </div>
          <div className="flex items-center space-x-4">
            {/* Temporary debug info for production troubleshooting */}
            {user && (
              <div className="text-xs text-gray-600 hidden lg:block">
                {user.first_name} | {user.role} | SU: {user.is_superuser ? 'Y' : 'N'}
              </div>
            )}
            <button
              onClick={logout}
              className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-md text-sm font-medium"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;