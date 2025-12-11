import React from 'react';
import { Route, Routes, useLocation, Navigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import Navbar from './components/Navbar';
import Login from './components/Login';
import LoginBranding from './components/LoginBranding';
import Dashboard from './components/Dashboard';
import LeaveRequest from './components/LeaveRequest';
import LeaveHistory from './components/LeaveHistory';
import MyProfile from './components/MyProfile';
import HRApprovals from './components/HRApprovals';
import ManagerDashboard from './components/ManagerDashboard';
import CEOApprovals from './components/CEOApprovals';
import StaffManagement from './components/StaffManagement';
import AdminSystemReset from './components/AdminSystemReset';
import AdminSettings from './components/AdminSettings';
import Skeleton from './components/common/Skeleton';
// import Unauthorized from './components/Unauthorized'; // Assuming this might not exist yet, defaulting to Navigate

// Protected Route Component
const ProtectedRoute = ({ children, roles }: { children: React.ReactElement, roles?: string[] }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="p-8 space-y-6">
         <Skeleton className="h-10 w-1/3 mb-8" />
         <div className="space-y-4">
            <Skeleton className="h-32 w-full rounded-xl" />
            <Skeleton className="h-64 w-full rounded-xl" />
         </div>
      </div>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (roles && !roles.includes(user.role) && !user.is_superuser) {
    return <Navigate to="/dashboard" replace />; // Redirect to dashboard instead of unauthorized for now
  }

  return children;
};

// Main Content Wrapper that uses hooks
const AppContent = () => {
  const location = useLocation();
  const isLoginPage = location.pathname === '/' || location.pathname === '/login';

  return (
    <div className="flex h-screen bg-app-bg overflow-hidden font-body">
      {/* Animated Sidebar - Desktop */}
      <motion.aside
        initial={false}
        animate={{ 
          width: isLoginPage ? "50%" : "18rem" // 288px = 18rem
        }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        className="hidden lg:flex bg-primary shadow-2xl z-20 flex-col overflow-hidden relative"
      >
        <AnimatePresence mode="wait">
          {isLoginPage ? (
            <motion.div
              key="login-brand"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
              className="w-full h-full"
            >
              <LoginBranding />
            </motion.div>
          ) : (
            <motion.div
              key="navbar"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
              className="w-full h-full"
            >
              <Navbar />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.aside>

      {/* Mobile Navbar Placeholder */}
      {!isLoginPage && (
        <div className="lg:hidden absolute top-0 left-0 z-50">
           <Navbar />
        </div>
      )}
      
      {/* Main Content Area */}
      <main className={`flex-1 relative z-10 h-full overflow-y-auto overflow-x-hidden ${isLoginPage ? '' : 'p-8'}`}>
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4, delay: 0.2 }}
            className="h-full"
          >
            <Routes location={location} key={location.pathname}>
              <Route path="/" element={<Login />} />
              <Route path="/login" element={<Login />} />
              
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/request"
                element={
                  <ProtectedRoute>
                    <LeaveRequest />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/history"
                element={
                  <ProtectedRoute>
                    <LeaveHistory />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/profile"
                element={
                  <ProtectedRoute>
                    <MyProfile />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/hr-approvals"
                element={
                  <ProtectedRoute roles={['hr']}>
                    <HRApprovals />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/manager"
                element={
                  <ProtectedRoute roles={['manager']}>
                    <ManagerDashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/ceo"
                element={
                  <ProtectedRoute roles={['ceo']}>
                    <CEOApprovals />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/staff"
                element={
                  <ProtectedRoute roles={['hr']}>
                    <StaffManagement />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/settings"
                element={
                  <ProtectedRoute roles={['admin']}>
                    <AdminSettings />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/system-reset"
                element={
                  <ProtectedRoute roles={['admin']}>
                    <AdminSystemReset />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<Navigate to="/" />} />
            </Routes>
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppContent />
      </ToastProvider>
    </AuthProvider>
  );
}

export default App;