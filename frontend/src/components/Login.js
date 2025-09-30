import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  // Show demo/test accounts only in development, or when explicitly enabled
  const showDemoLogins =
    process.env.REACT_APP_SHOW_DEMO_LOGINS === 'true' ||
    process.env.NODE_ENV !== 'production';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(email, password);
    
    if (result.success) {
      navigate('/dashboard');
    } else {
      setError(result.error);
    }
    
    setLoading(false);
  };

  const quickLogin = (userEmail, userPassword) => {
    setEmail(userEmail);
    setPassword(userPassword);
  };

  return (
    <div className="min-h-screen relative grid place-items-center bg-gray-50 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="text-center text-3xl font-extrabold text-gray-900">
            Leave Management System
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Sign in to your account
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}
          
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <input
                id="email"
                name="email"
                type="email"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-primary-500 focus:border-primary-500 focus:z-10 sm:text-sm"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <input
                id="password"
                name="password"
                type="password"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-primary-500 focus:border-primary-500 focus:z-10 sm:text-sm"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </div>
        </form>

        {showDemoLogins && (
          <div className="mt-6">
            <div className="text-center text-sm text-gray-600 mb-4">
              Test Accounts (Development):
            </div>
            <div className="space-y-2">
              <button
                type="button"
                onClick={() => quickLogin('john.doe@company.com', 'password123')}
                className="w-full text-left px-3 py-2 text-sm bg-blue-50 border border-blue-200 rounded hover:bg-blue-100"
              >
                <strong>Employee:</strong> john.doe@company.com / password123
              </button>
              <button
                type="button"
                onClick={() => quickLogin('manager@company.com', 'password123')}
                className="w-full text-left px-3 py-2 text-sm bg-green-50 border border-green-200 rounded hover:bg-green-100"
              >
                <strong>Manager:</strong> manager@company.com / password123
              </button>
              <button
                type="button"
                onClick={() => quickLogin('hr@company.com', 'password123')}
                className="w-full text-left px-3 py-2 text-sm bg-purple-50 border border-purple-200 rounded hover:bg-purple-100"
              >
                <strong>HR:</strong> hr@company.com / password123
              </button>
            </div>
          </div>
        )}
      </div>
      {/* DigitalOcean referral badge */}
      <a
        href="https://www.digitalocean.com/?refcode=b763faf71d52&utm_campaign=Referral_Invite&utm_medium=Referral_Program&utm_source=badge"
        target="_blank"
        rel="noopener noreferrer"
        className="hidden sm:block fixed bottom-4 right-4 opacity-80 hover:opacity-100 transition"
        aria-label="DigitalOcean Referral Badge"
      >
        <img
          src="https://web-platforms.sfo2.cdn.digitaloceanspaces.com/WWW/Badge%201.svg"
          alt="DigitalOcean Referral Badge"
          className="h-12 w-auto drop-shadow"
        />
      </a>
    </div>
  );
}

export default Login;