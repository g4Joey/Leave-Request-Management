import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';

function AdminSystemReset() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [confirmText, setConfirmText] = useState('');
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [result, setResult] = useState(null);

  // Only show for admin users
  if (!user || (!user.is_superuser && user.role !== 'admin')) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-red-900 mb-2">Access Denied</h3>
        <p className="text-red-700">Only administrators can access the system reset feature.</p>
      </div>
    );
  }

  const handleReset = async () => {
    if (confirmText !== 'yes, reset everything') {
      alert('Please type the exact confirmation text: "yes, reset everything"');
      return;
    }

    setLoading(true);
    try {
      // System reset endpoint lives under requests viewset
      const response = await api.post('/leaves/requests/system_reset/', {
        confirm_reset: confirmText
      });

      setResult({
        success: true,
        data: response.data
      });
      setShowConfirmation(false);
      setConfirmText('');
    } catch (error) {
      setResult({
        success: false,
        error: error.response?.data?.error || 'System reset failed'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Admin System Reset</h2>
          <p className="text-sm text-gray-600 mt-1">
            Reset the leave management system to default state for testing purposes
          </p>
        </div>

        <div className="p-6">
          {!showConfirmation ? (
            <div className="space-y-6">
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-start">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-yellow-800">
                      Warning: Destructive Action
                    </h3>
                    <div className="mt-2 text-sm text-yellow-700">
                      <p>This action will:</p>
                      <ul className="list-disc list-inside mt-1 space-y-1">
                        <li>Delete ALL leave requests from the system</li>
                        <li>Reset ALL user leave balances (keep entitlements, clear used/pending days)</li>
                        <li>Clear all approval histories and comments</li>
                      </ul>
                      <p className="mt-2 font-medium">This action cannot be undone!</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-900 mb-2">What will be reset:</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-700">
                  <div>
                    <h5 className="font-medium">Leave Requests:</h5>
                    <ul className="mt-1 space-y-1">
                      <li>• All pending requests</li>
                      <li>• All approved requests</li>
                      <li>• All rejected requests</li>
                      <li>• All cancelled requests</li>
                    </ul>
                  </div>
                  <div>
                    <h5 className="font-medium">Leave Balances:</h5>
                    <ul className="mt-1 space-y-1">
                      <li>• Used days → 0</li>
                      <li>• Pending days → 0</li>
                      <li>• Entitled days (preserved)</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div className="flex justify-center">
                <button
                  onClick={() => setShowConfirmation(true)}
                  className="bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-lg font-medium focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                >
                  Proceed to System Reset
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <h3 className="text-lg font-medium text-red-900 mb-2">Final Confirmation Required</h3>
                <p className="text-red-700 mb-4">
                  To proceed with the system reset, type exactly: 
                  <code className="bg-red-100 px-2 py-1 rounded ml-2 font-mono">yes, reset everything</code>
                </p>
                <input
                  type="text"
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  placeholder="Type confirmation text here..."
                  className="w-full px-3 py-2 border border-red-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
                  disabled={loading}
                />
              </div>

              <div className="flex justify-between">
                <button
                  onClick={() => {
                    setShowConfirmation(false);
                    setConfirmText('');
                  }}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  disabled={loading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleReset}
                  disabled={loading || confirmText !== 'yes, reset everything'}
                  className="bg-red-600 hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-6 py-2 rounded-md font-medium focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                >
                  {loading ? 'Resetting System...' : 'Reset System Now'}
                </button>
              </div>
            </div>
          )}

          {result && (
            <div className={`mt-6 p-4 rounded-lg ${result.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
              {result.success ? (
                <div>
                  <h3 className="text-lg font-medium text-green-900 mb-2">System Reset Completed</h3>
                  <div className="text-green-700 space-y-1">
                    <p>✓ Deleted {result.data.deleted_requests} leave requests</p>
                    <p>✓ Reset {result.data.reset_balances} leave balances</p>
                    <p>Performed by: {result.data.performed_by}</p>
                    <p>Timestamp: {new Date(result.data.timestamp).toLocaleString()}</p>
                  </div>
                </div>
              ) : (
                <div>
                  <h3 className="text-lg font-medium text-red-900 mb-2">Reset Failed</h3>
                  <p className="text-red-700">{result.error}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AdminSystemReset;