import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Link, useLocation } from 'react-router-dom';
import { useApprovalCounts } from '../hooks/useApprovalCounts';
import { 
  LayoutDashboard, 
  PlusCircle, 
  History, 
  User, 
  Users, 
  FileCheck, 
  ShieldAlert, 
  Settings, 
  LogOut,
  Menu,
  X
} from 'lucide-react';

function Navbar() {
  const { logout, user } = useAuth();
  const location = useLocation();
  const { counts } = useApprovalCounts();
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const isActive = (path: string) => location.pathname === path;

  // Helper for Badge
  const BadgeCount = ({ count }: { count: number }) => {
    if (!count || count === 0) return null;
    return (
      <span className="ml-auto bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full min-w-[20px] text-center">
        {count > 99 ? '99+' : count}
      </span>
    );
  };

  // Helper for Nav Items
  const NavItem = ({ to, icon: Icon, label, count }: { to: string, icon: any, label: string, count?: number }) => (
    <Link
      to={to}
      onClick={() => setIsMobileOpen(false)}
      className={`group flex items-center px-3 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
        isActive(to)
          ? 'bg-white/10 text-white shadow-lg backdrop-blur-sm'
          : 'text-white/70 hover:bg-white/5 hover:text-white'
      }`}
    >
      <Icon className={`mr-3 h-5 w-5 flex-shrink-0 transition-colors ${isActive(to) ? 'text-accent' : 'text-white/50 group-hover:text-white'}`} />
      <span className="flex-1">{label}</span>
      <BadgeCount count={count || 0} />
    </Link>
  );

  return (
    <>
      {/* Mobile Toggle Button */}
      <div className="lg:hidden fixed top-4 left-4 z-50">
        <button
          onClick={() => setIsMobileOpen(!isMobileOpen)}
          className="p-2 rounded-lg bg-primary text-white shadow-lg hover:bg-primary/90 transition-colors"
        >
          {isMobileOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Overlay for mobile */}
      {isMobileOpen && (
        <div 
          className="lg:hidden fixed inset-0 bg-black/50 z-40 backdrop-blur-sm"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar Container - Fills parent (which is animated) */}
      <div className={`fixed lg:static inset-y-0 left-0 z-40 w-72 lg:w-full bg-primary transform transition-transform duration-300 ease-in-out lg:transform-none flex flex-col h-screen lg:h-full ${
        isMobileOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        {/* Logo Section */}
        <div className="flex items-center justify-center h-32 border-b border-white/10 p-6">
          <img 
            src="/leavemateLogo.png" 
            alt="LeaveMates Logo" 
            className="h-16 w-16 mb-2 object-contain drop-shadow-lg"
            onError={(e) => {
              // Fallback if image fails
              e.currentTarget.style.display = 'none'; 
              e.currentTarget.parentElement?.classList.add('fallback-text-only');
            }}
          />
          <span className="text-2xl font-bold font-heading text-white tracking-wide">LeaveMates</span>
        </div>

        {/* Navigation Section */}
        <div className="flex-1 overflow-y-auto py-6 px-4 space-y-1 custom-scrollbar">
          <NavItem to="/dashboard" icon={LayoutDashboard} label="Dashboard" />
          
          {user?.role !== 'ceo' && (
            <>
              <NavItem to="/request" icon={PlusCircle} label="Request Leave" />
              <NavItem to="/history" icon={History} label="Leave History" />
            </>
          )}

          {user && (
            <NavItem to="/profile" icon={User} label="My Profile" />
          )}

          {/* Separator for Approvals */}
          {(user?.role === 'hr' || user?.role === 'manager' || user?.role === 'ceo' || user?.is_superuser) && (
             <div className="pt-6 pb-2">
               <p className="px-3 text-xs font-semibold text-white/40 uppercase tracking-wider">Management</p>
             </div>
          )}

          {/* Role Based Links */}
          {(user?.role === 'hr' || user?.is_superuser) && (
             <NavItem to="/hr-approvals" icon={FileCheck} label="HR Approvals" count={counts.hr_approvals} />
          )}
          
          {(user?.role === 'manager' || user?.is_superuser) && (
             <NavItem to="/manager" icon={FileCheck} label="Manager Approvals" count={counts.manager_approvals} />
          )}

          {(user?.role === 'ceo' || user?.is_superuser) && (
             <NavItem to="/ceo" icon={ShieldAlert} label="CEO Approvals" count={counts.ceo_approvals} />
          )}

          {(user?.role === 'hr' || user?.is_superuser) && (
             <NavItem to="/staff" icon={Users} label="Staff Directory" />
          )}

          {(user?.role === 'admin' || user?.is_superuser) && (
             <>
                <div className="pt-6 pb-2">
                  <p className="px-3 text-xs font-semibold text-white/40 uppercase tracking-wider">Administration</p>
                </div>
                <NavItem to="/admin/settings" icon={Settings} label="System Settings" />
                <NavItem to="/admin/system-reset" icon={ShieldAlert} label="System Reset" />
             </>
          )}
        </div>

        {/* Footer / User User Section */}
        <div className="border-t border-white/10 p-4 bg-black/10">
          <div className="flex items-center gap-3 mb-4 px-2">
            <div className="w-10 h-10 rounded-full bg-accent/20 flex items-center justify-center text-accent font-bold">
              {user?.first_name?.charAt(0) || 'U'}
            </div>
            <div className="flex-1 overflow-hidden">
              <p className="text-sm font-medium text-white truncate">{user?.first_name} {user?.last_name}</p>
              <p className="text-xs text-white/50 truncate capitalize">{user?.role_display || user?.role}</p>
            </div>
          </div>
          
          <button
            onClick={logout}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-white/80 bg-white/5 hover:bg-red-500/20 hover:text-red-100 rounded-lg transition-all duration-200"
          >
            <LogOut size={18} />
            <span>Sign Out</span>
          </button>
        </div>
      </div>
    </>
  );
}

export default Navbar;