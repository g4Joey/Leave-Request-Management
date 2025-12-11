import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Leaf, ArrowRight } from 'lucide-react';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  // Demo accounts disabled per user request
  const showDemoLogins = false;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(email, password);

    if (result.success) {
      navigate('/dashboard');
    } else {
      setError(result.error || 'Login failed');
    }

    setLoading(false);
  };

  const quickLogin = (userEmail: string, userPassword: string) => {
    setEmail(userEmail);
    setPassword(userPassword);
  };

  return (
    <div className="w-full h-full flex items-center justify-center p-8 bg-white">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center lg:text-left">
          <div className="lg:hidden flex justify-center mb-6">
            <div className="bg-primary/5 p-3 rounded-xl">
              <Leaf className="w-10 h-10 text-primary" />
            </div>
          </div>
          <h2 className="text-3xl font-bold text-gray-900 font-heading">Welcome Back</h2>
          <p className="mt-2 text-gray-600">Please enter your details to sign in.</p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg">
              <div className="flex">
                <div className="ml-3">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                className="input-field"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                className="input-field"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <input
                id="remember-me"
                name="remember-me"
                type="checkbox"
                className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
              />
              <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-900">
                Remember me
              </label>
            </div>

            <div className="text-sm">
              <a href="#" className="font-medium text-primary hover:text-primary/80">
                Forgot password?
              </a>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="group w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-bold text-white bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50 transition-all duration-200"
          >
            {loading ? (
              <span className="flex items-center gap-2 animate-pulse">
                <span className="h-2 w-2 bg-white rounded-full animate-bounce"></span>
                <span className="h-2 w-2 bg-white rounded-full animate-bounce delay-75"></span>
                <span className="h-2 w-2 bg-white rounded-full animate-bounce delay-150"></span>
                <span className="ml-2">Signing In...</span>
              </span>
            ) : (
              'Sign in'
            )}
          </button>
        </form>

        {showDemoLogins && (
          <div className="mt-8 border-t border-gray-100 pt-6">
            <p className="text-xs text-center text-gray-400 uppercase tracking-wider mb-4 font-semibold">
              Demo Accounts
            </p>
            <div className="grid grid-cols-1 gap-3">
              <button
                type="button"
                onClick={() => quickLogin('john.doe@company.com', 'password123')}
                className="flex items-center justify-between w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg transition-colors group"
              >
                <div className="flex flex-col items-start">
                  <span className="text-sm font-semibold text-gray-900">Employee</span>
                  <span className="text-xs text-gray-500">john.doe@company.com</span>
                </div>
                <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-primary transition-colors" />
              </button>
              <button
                type="button"
                onClick={() => quickLogin('manager@company.com', 'password123')}
                className="flex items-center justify-between w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg transition-colors group"
              >
                <div className="flex flex-col items-start">
                  <span className="text-sm font-semibold text-gray-900">Manager</span>
                  <span className="text-xs text-gray-500">manager@company.com</span>
                </div>
                <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-primary transition-colors" />
              </button>
              <button
                type="button"
                onClick={() => quickLogin('hr@company.com', 'password123')}
                className="flex items-center justify-between w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg transition-colors group"
              >
                <div className="flex flex-col items-start">
                  <span className="text-sm font-semibold text-gray-900">HR Admin</span>
                  <span className="text-xs text-gray-500">hr@company.com</span>
                </div>
                <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-primary transition-colors" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
export default Login;