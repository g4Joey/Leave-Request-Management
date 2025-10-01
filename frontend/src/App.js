import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import LeaveRequest from './components/LeaveRequest';
import LeaveHistory from './components/LeaveHistory';
import ManagerDashboard from './components/ManagerDashboard';
import StaffManagement from './components/StaffManagement';
import MyProfile from './components/MyProfile';
import Navbar from './components/Navbar';
import { ToastProvider } from './contexts/ToastContext';
import ErrorBoundary from './components/ErrorBoundary';

function ProtectedRoute({ children }) {
  const { user } = useAuth();
  return user ? children : <Navigate to="/login" />;
}

function ManagerRoute({ children }) {
  const { user } = useAuth();
  const allowed = user && (user.role === 'manager' || user.is_superuser);
  return allowed ? children : <Navigate to="/dashboard" />;
}

function HRRoute({ children }) {
  const { user } = useAuth();
  const allowed = user && (user.role === 'hr' || user.is_superuser);
  return allowed ? children : <Navigate to="/dashboard" />;
}

function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <ErrorBoundary>
          <Router>
            <div className="min-h-screen bg-gray-50">
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route
                path="/*"
                element={
                  <ProtectedRoute>
                    <div className="flex flex-col min-h-screen">
                      <Navbar />
                      <main className="flex-1 container mx-auto px-4 py-8">
                        <Routes>
                          <Route path="/" element={<Dashboard />} />
                          <Route path="/dashboard" element={<Dashboard />} />
                          <Route path="/request" element={<LeaveRequest />} />
                          <Route path="/history" element={<LeaveHistory />} />
                          <Route path="/profile" element={<MyProfile />} />
                          <Route
                            path="/manager"
                            element={
                              <ManagerRoute>
                                <ManagerDashboard />
                              </ManagerRoute>
                            }
                          />
                          <Route
                            path="/staff"
                            element={
                              <HRRoute>
                                <StaffManagement />
                              </HRRoute>
                            }
                          />
                        </Routes>
                      </main>
                    </div>
                  </ProtectedRoute>
                }
              />
            </Routes>
            </div>
          </Router>
        </ErrorBoundary>
      </ToastProvider>
    </AuthProvider>
  );
}

export default App;