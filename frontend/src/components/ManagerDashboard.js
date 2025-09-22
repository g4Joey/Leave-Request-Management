import React, { useState, useEffect } from 'react';
import api from '../services/api';

function ManagerDashboard() {
  const [pendingRequests, setPendingRequests] = useState([]);
  const [approvedRequests, setApprovedRequests] = useState([]);
  const [rejectedRequests, setRejectedRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  // Track which action is loading per request id: 'approve' | 'reject' | undefined
  const [loadingActionById, setLoadingActionById] = useState({});
  // Accessible message shown after actions
  const [feedback, setFeedback] = useState(null); // { type: 'success'|'error', text: string }

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [pendingRes, approvedRes, rejectedRes] = await Promise.all([
          api.get('/leaves/manager/pending_approvals/'),
          api.get('/leaves/manager/', { params: { status: 'approved', ordering: '-created_at', limit: 10 } }),
          api.get('/leaves/manager/', { params: { status: 'rejected', ordering: '-created_at', limit: 10 } }),
        ]);
        setPendingRequests(pendingRes.data.results || pendingRes.data);
        setApprovedRequests(approvedRes.data.results || approvedRes.data);
        setRejectedRequests(rejectedRes.data.results || rejectedRes.data);
      } catch (error) {
        console.error('Error fetching pending requests:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAll();
  }, []);

  const refreshApprovedRejected = async () => {
    try {
      const [approvedRes, rejectedRes] = await Promise.all([
        api.get('/leaves/manager/', { params: { status: 'approved', ordering: '-created_at', limit: 10 } }),
        api.get('/leaves/manager/', { params: { status: 'rejected', ordering: '-created_at', limit: 10 } }),
      ]);
      setApprovedRequests(approvedRes.data.results || approvedRes.data);
      setRejectedRequests(rejectedRes.data.results || rejectedRes.data);
    } catch (e) {
      // non-blocking
    }
  };

  const handleAction = async (requestId, action, comments = '') => {
    setLoadingActionById((prev) => ({ ...prev, [requestId]: action }));

    try {
      await api.put(`/leaves/manager/${requestId}/${action}/`, {
        approval_comments: comments || ''
      });
      
      // Remove the request from the list
      setPendingRequests(prev => prev.filter(req => req.id !== requestId));
      // Refresh approved/rejected sections to reflect the change
      refreshApprovedRejected();
      // Accessible feedback + optional haptics
      setFeedback({ type: 'success', text: `Request ${action}ed successfully.` });
      if (navigator && 'vibrate' in navigator) {
        try { navigator.vibrate(40); } catch (_) { /* noop */ }
      }
    } catch (error) {
      console.error(`Error ${action}ing request:`, error);
      const detail = error?.response?.data?.error || error?.response?.data?.detail || '';
      setFeedback({ type: 'error', text: `Failed to ${action} request${detail ? `: ${detail}` : ''}` });
      if (navigator && 'vibrate' in navigator) {
        try { navigator.vibrate([20, 40, 20]); } catch (_) { /* noop */ }
      }
    } finally {
      setLoadingActionById((prev) => ({ ...prev, [requestId]: undefined }));
    }
  };

  const getEmployeeName = (request) => {
    return request?.employee_name || request?.employee_email || 'Unknown Employee';
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
      {/* Accessible feedback region */}
      {feedback && (
        <div
          className={`mx-4 mb-4 rounded-md p-4 border flex items-start gap-3 ${
            feedback.type === 'success'
              ? 'bg-green-50 border-green-300'
              : 'bg-red-50 border-red-300'
          }`}
          role="status"
          aria-live="polite"
        >
          <span
            className={`inline-flex h-5 w-5 flex-none items-center justify-center rounded-full text-xs font-bold ${
              feedback.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
            }`}
            aria-hidden="true"
          >
            {feedback.type === 'success' ? '✓' : '!'}
          </span>
          <span className="text-sm text-gray-900">
            {feedback.text}
          </span>
          <button
            onClick={() => setFeedback(null)}
            className="ml-auto text-sm underline text-gray-600 hover:text-gray-900"
          >
            Dismiss
          </button>
        </div>
      )}
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
                          {getEmployeeName(request)}
                        </p>
                        <p className="text-sm text-gray-900">
                          {request.leave_type_name || 'Leave Request'}
                        </p>
                        <p className="text-sm text-gray-500">
                          {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()}
                          <span className="ml-2">({request.total_days} working days)</span>
                        </p>
                      </div>
                      <div className="flex space-x-2">
                        <button
                          onClick={() => handleAction(request.id, 'approve')}
                          disabled={Boolean(loadingActionById[request.id])}
                          className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
                        >
                          {loadingActionById[request.id] === 'approve' ? 'Processing...' : 'Approve'}
                        </button>
                        <button
                          onClick={() => {
                            const comments = prompt('Rejection reason (optional):');
                            if (comments !== null) {
                              handleAction(request.id, 'reject', comments);
                            }
                          }}
                          disabled={Boolean(loadingActionById[request.id])}
                          className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
                        >
                          {loadingActionById[request.id] === 'reject' ? 'Processing...' : 'Reject'}
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

      {/* Approved & Rejected sections */}
      <div className="px-4 py-5 sm:px-6">
        <h4 className="text-md leading-6 font-semibold text-gray-900">Recently Approved</h4>
      </div>
      <ul className="divide-y divide-gray-200">
        {approvedRequests.length > 0 ? (
          approvedRequests.map((request) => (
            <li key={`approved-${request.id}`}>
              <div className="px-4 py-3 sm:px-6 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {getEmployeeName(request)} — {request.leave_type_name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()} ({request.total_days} days)
                  </p>
                </div>
                <span className="inline-flex items-center rounded-md bg-green-100 px-2 py-1 text-xs font-medium text-green-800 ring-1 ring-inset ring-green-200">
                  Approved
                </span>
              </div>
            </li>
          ))
        ) : (
          <li><div className="px-4 py-3 text-sm text-gray-500">No approved requests yet.</div></li>
        )}
      </ul>

      <div className="px-4 py-5 sm:px-6">
        <h4 className="text-md leading-6 font-semibold text-gray-900">Recently Rejected</h4>
      </div>
      <ul className="divide-y divide-gray-200">
        {rejectedRequests.length > 0 ? (
          rejectedRequests.map((request) => (
            <li key={`rejected-${request.id}`}>
              <div className="px-4 py-3 sm:px-6 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {getEmployeeName(request)} — {request.leave_type_name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()} ({request.total_days} days)
                  </p>
                </div>
                <span className="inline-flex items-center rounded-md bg-red-100 px-2 py-1 text-xs font-medium text-red-800 ring-1 ring-inset ring-red-200">
                  Rejected
                </span>
              </div>
            </li>
          ))
        ) : (
          <li><div className="px-4 py-3 text-sm text-gray-500">No rejected requests yet.</div></li>
        )}
      </ul>
    </div>
  );
}

export default ManagerDashboard;