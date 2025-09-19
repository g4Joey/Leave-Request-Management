import React, { useState, useEffect } from 'react';
import api from '../services/api';

function ManagerDashboard() {
  const [pendingRequests, setPendingRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState({});

  useEffect(() => {
    const fetchPendingRequests = async () => {
      try {
        const response = await api.get('/leaves/manager/pending_approvals/');
        setPendingRequests(response.data.results || response.data);
      } catch (error) {
        console.error('Error fetching pending requests:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchPendingRequests();
  }, []);

  const handleAction = async (requestId, action, comments = '') => {
    setActionLoading({ ...actionLoading, [requestId]: true });

    try {
      await api.put(`/leaves/manager/${requestId}/${action}/`, {
        manager_comments: comments
      });
      
      // Remove the request from the list
      setPendingRequests(prev => prev.filter(req => req.id !== requestId));
    } catch (error) {
      console.error(`Error ${action}ing request:`, error);
      alert(`Failed to ${action} request`);
    } finally {
      setActionLoading({ ...actionLoading, [requestId]: false });
    }
  };

  const getEmployeeName = (employee) => {
    return employee?.email || 'Unknown Employee';
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="bg-white shadow overflow-hidden sm:rounded-md">
      <div className="px-4 py-5 sm:px-6">
        <h3 className="text-lg leading-6 font-medium text-gray-900">
          Manager Dashboard
        </h3>
        <p className="mt-1 max-w-2xl text-sm text-gray-500">
          Review and approve pending leave requests.
        </p>
      </div>
      <ul className="divide-y divide-gray-200">
        {pendingRequests.length > 0 ? (
          pendingRequests.map((request) => (
            <li key={request.id}>
              <div className="px-4 py-4 sm:px-6">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-primary-600">
                          {getEmployeeName(request.employee)}
                        </p>
                        <p className="text-sm text-gray-900">
                          {request.leave_type?.name || 'Leave Request'}
                        </p>
                        <p className="text-sm text-gray-500">
                          {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()}
                          <span className="ml-2">({request.working_days} working days)</span>
                        </p>
                      </div>
                      <div className="flex space-x-2">
                        <button
                          onClick={() => handleAction(request.id, 'approve')}
                          disabled={actionLoading[request.id]}
                          className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
                        >
                          {actionLoading[request.id] ? 'Processing...' : 'Approve'}
                        </button>
                        <button
                          onClick={() => {
                            const comments = prompt('Rejection reason (optional):');
                            if (comments !== null) {
                              handleAction(request.id, 'reject', comments);
                            }
                          }}
                          disabled={actionLoading[request.id]}
                          className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
                        >
                          {actionLoading[request.id] ? 'Processing...' : 'Reject'}
                        </button>
                      </div>
                    </div>
                    {request.reason && (
                      <div className="mt-2">
                        <p className="text-sm text-gray-600">
                          <strong>Reason:</strong> {request.reason}
                        </p>
                      </div>
                    )}
                    <div className="mt-2 text-xs text-gray-400">
                      Submitted: {new Date(request.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>
              </div>
            </li>
          ))
        ) : (
          <li>
            <div className="px-4 py-8 text-center text-gray-500">
              No pending leave requests to review.
            </div>
          </li>
        )}
      </ul>
    </div>
  );
}

export default ManagerDashboard;