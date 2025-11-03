import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Link, useLocation } from 'react-router-dom';
import { useApprovalCounts } from '../hooks/useApprovalCounts';

function Navbar() {
  const { logout, user } = useAuth();
  const location = useLocation();
  const { counts } = useApprovalCounts();

  const isActive = (path) => location.pathname === path;

  const BadgeCount = ({ count }) => {
    if (!count || count === 0) return null;
    return (
      <span className="ml-1 bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5 min-w-[16px] h-4 flex items-center justify-center">
        {count > 99 ? '99+' : count}
      </span>
    );
  };
  


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
              {user?.role !== 'ceo' && (
                <>
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
                </>
              )}
              {user && (
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
              )}

              {(() => {
                const role = user?.role;
                const canSeeHRApprovals = !!user && (role === 'hr' || user.is_superuser === true);
                return canSeeHRApprovals && (
                  <Link
                    to="/hr-approvals"
                    className={`${
                      isActive('/hr-approvals')
                        ? 'border-primary-500 text-gray-900'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
                  >
                    HR Approvals
                    <BadgeCount count={counts.hr_approvals} />
                  </Link>
                );
              })()}

              {(() => {
                const role = user?.role;
                const canSeeManager = !!user && (role === 'manager' || user.is_superuser === true);
                return canSeeManager && (
                  <Link
                    to="/manager"
                    className={`${
                      isActive('/manager')
                        ? 'border-primary-500 text-gray-900'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
                  >
                    Manager Approvals
                    <BadgeCount count={counts.manager_approvals} />
                  </Link>
                );
              })()}
              {(() => {
                const role = user?.role;
                const canSeeCEO = !!user && (role === 'ceo' || user.is_superuser === true);
                return canSeeCEO && (
                  <Link
                    to="/ceo"
                    className={`${
                      isActive('/ceo')
                        ? 'border-primary-500 text-gray-900'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
                  >
                    CEO Approvals
                    <BadgeCount count={counts.ceo_approvals} />
                  </Link>
                );
              })()}
              {(() => {
                const role = user?.role;
                const canSeeStaff = !!user && (role === 'hr' || user.is_superuser === true);
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
              {(() => {
                const role = user?.role;
                const canSeeAdmin = !!user && (role === 'admin' || user.is_superuser === true);
                return canSeeAdmin && (
                  <>
                    <Link
                      to="/admin/settings"
                      className={`${
                        isActive('/admin/settings')
                          ? 'border-primary-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
                    >
                      Admin Settings
                    </Link>
                    <Link
                      to="/admin/system-reset"
                      className={`${
                        isActive('/admin/system-reset')
                          ? 'border-primary-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
                    >
                      Admin Reset
                    </Link>
                  </>
                );
              })()}
            </div>
          </div>
          <div className="flex items-center space-x-4">

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