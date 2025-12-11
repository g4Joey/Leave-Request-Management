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
  const linkClass = 'inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium';
  


  return (
    <nav className="shadow-lg" style={{ backgroundColor: 'var(--nav-bg)', color: 'var(--nav-text)' }}>
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <h1 className="text-2xl font-bold text-gray-800" style={{ marginLeft: '-12px' }}>
                Leave Management
              </h1>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              <Link
                to="/dashboard"
                className={linkClass}
                style={isActive('/dashboard') || isActive('/') ? { borderBottomColor: 'var(--primary)', color: 'var(--primary)' } : {}}
              >
                Dashboard
              </Link>
              {(() => {
                const isCEO = user?.role === 'ceo';
                const aff = (user?.affiliate_name || '').toUpperCase();
                const ceoCanRequest = isCEO && (aff === 'SDSL' || aff === 'SBL');
                const allowRequest = !isCEO || ceoCanRequest; // block only Merban CEO
                return allowRequest;
              })() && (
                <>
                  <Link
                    to="/request"
                    className={linkClass}
                    style={isActive('/request') ? { borderBottomColor: 'var(--primary)', color: 'var(--primary)' } : {}}
                  >
                    Request Leave
                  </Link>
                  <Link
                    to="/history"
                    className={linkClass}
                    style={isActive('/history') ? { borderBottomColor: 'var(--primary)', color: 'var(--primary)' } : {}}
                  >
                    Leave History
                    <BadgeCount count={counts.recall_pending} />
                  </Link>
                </>
              )}
              {user && (
                <Link
                    to="/profile"
                    className={linkClass}
                    style={isActive('/profile') ? { borderBottomColor: 'var(--primary)', color: 'var(--primary)' } : {}}
                  >
                    My Profile
                  </Link>
              )}

              {(() => {
                const role = user?.role;
                const canSeeManager = !!user && (role === 'manager' || role === 'hr' || user.is_superuser === true);
                return canSeeManager && (
                    <Link
                      to="/manager"
                      className={linkClass}
                      style={isActive('/manager') ? { borderBottomColor: 'var(--primary)', color: 'var(--primary)' } : {}}
                    >
                      Manager Approvals
                      <BadgeCount count={counts.manager_approvals} />
                    </Link>
                );
              })()}
              {(() => {
                const role = user?.role;
                const canSeeHRApprovals = !!user && (role === 'hr' || user.is_superuser === true);
                return canSeeHRApprovals && (
                    <Link
                      to="/hr-approvals"
                      className={linkClass}
                      style={isActive('/hr-approvals') ? { borderBottomColor: 'var(--primary)', color: 'var(--primary)' } : {}}
                    >
                      HR Approvals
                      <BadgeCount count={counts.hr_approvals} />
                    </Link>
                );
              })()}
              {(() => {
                const role = user?.role;
                const canSeeCEO = !!user && (role === 'ceo' || user.is_superuser === true);
                return canSeeCEO && (
                    <Link
                      to="/ceo"
                      className={linkClass}
                      style={isActive('/ceo') ? { borderBottomColor: 'var(--primary)', color: 'var(--primary)' } : {}}
                    >
                      CEO Approvals
                      <BadgeCount count={counts.ceo_approvals} />
                    </Link>
                );
              })()}
              {user?.is_superuser && (
                <>
                  <Link
                    to="/ceo/sdsl"
                    className={linkClass}
                    style={isActive('/ceo/sdsl') ? { borderBottomColor: 'var(--primary)', color: 'var(--primary)' } : {}}
                  >
                    SDSL CEO Approvals
                  </Link>
                  <Link
                    to="/ceo/sbl"
                    className={linkClass}
                    style={isActive('/ceo/sbl') ? { borderBottomColor: 'var(--primary)', color: 'var(--primary)' } : {}}
                  >
                    SBL CEO Approvals
                  </Link>
                </>
              )}
              {(() => {
                const role = user?.role;
                const canSeeStaff = !!user && (role === 'hr' || user.is_superuser === true);
                return canSeeStaff && (
                    <Link
                      to="/staff"
                      className={linkClass}
                      style={isActive('/staff') ? { borderBottomColor: 'var(--primary)', color: 'var(--primary)' } : {}}
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
                      className={linkClass}
                      style={isActive('/admin/settings') ? { borderBottomColor: 'var(--primary)', color: 'var(--primary)' } : {}}
                    >
                      Admin Settings
                    </Link>
                    <Link
                      to="/admin/system-reset"
                      className={linkClass}
                      style={isActive('/admin/system-reset') ? { borderBottomColor: 'var(--primary)', color: 'var(--primary)' } : {}}
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
              className="btn-primary"
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