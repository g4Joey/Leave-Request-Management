import React, { useState, useEffect } from 'react';
import { useToast } from '../contexts/ToastContext';
import api from '../services/api';

function LeaveHistory() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [cancelModal, setCancelModal] = useState({ open: false, request: null, comments: '', loading: false });
  const { showToast } = useToast();

  useEffect(() => {
    const fetchRequests = async () => {
      try {
        const response = await api.get('/leaves/requests/history/');
        setRequests(response.data.results || response.data);
      } catch (error) {
        console.error('Error fetching leave history:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchRequests();
  }, []);

  const getStatusColor = (status) => {
    const colors = {
      'pending': 'bg-yellow-100 text-yellow-800',
      'manager_approved': 'bg-blue-100 text-blue-800',
      'hr_approved': 'bg-purple-100 text-purple-800',
      'approved': 'bg-green-100 text-green-800',
      'rejected': 'bg-red-100 text-red-800',
      'cancelled': 'bg-gray-100 text-gray-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const canCancel = (request) => {
    return request.status === 'pending';
  };

  const handleCancelRequest = async () => {
    if (!cancelModal.request) return;
    
    try {
      setCancelModal(prev => ({ ...prev, loading: true }));
      await api.put(`/leaves/manager/${cancelModal.request.id}/cancel/`, {
        comments: cancelModal.comments
      });
      
      // Refresh the requests list
      const response = await api.get('/leaves/requests/history/');
      setRequests(response.data.results || response.data);
      
      setCancelModal({ open: false, request: null, comments: '', loading: false });
      showToast('Leave request cancelled successfully', 'success');
    } catch (error) {
      console.error('Error cancelling request:', error);
      setCancelModal(prev => ({ ...prev, loading: false }));
      showToast(error.response?.data?.error || 'Failed to cancel request', 'error');
    }
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
          Leave History
        </h3>
        <p className="mt-1 max-w-2xl text-sm text-gray-500">
          All your leave requests and their current status.
        </p>
      </div>
      <ul className="divide-y divide-gray-200">
        {requests.length > 0 ? (
          requests.map((request) => (
            <li key={request.id}>
              <div className="px-4 py-4 sm:px-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(request.status)}`}>
                        {request.status}
                      </span>
                    </div>
                    <div className="ml-4">
                      <div className="text-sm font-medium text-gray-900">
                        {request.leave_type_name || 'Leave Request'}
                      </div>
                      <div className="text-sm text-gray-500">
                        {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-sm text-gray-500">
                      {request.working_days} working days
                    </div>
                    {canCancel(request) && (
                      <button
                        onClick={() => setCancelModal({ open: true, request, comments: '', loading: false })}
                        className="text-sm text-red-600 hover:text-red-800 font-medium"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
                {request.reason && (
                  <div className="mt-2 text-sm text-gray-600">
                    <strong>Reason:</strong> {request.reason}
                  </div>
                )}
                {request.manager_comments && (
                  <div className="mt-2 text-sm text-gray-600">
                    <strong>HOD Comments:</strong> {request.manager_comments}
                  </div>
                )}
                <div className="mt-2 text-xs text-gray-400">
                  Submitted: {new Date(request.created_at).toLocaleString()}
                </div>
              </div>
            </li>
          ))
        ) : (
          <li>
            <div className="px-4 py-8 text-center text-gray-500">
              No leave requests found.
            </div>
          </li>
        )}
      </ul>

      {/* Cancel Modal */}
      {cancelModal.open && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Cancel Leave Request
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                Are you sure you want to cancel this leave request? This action cannot be undone.
              </p>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Reason for cancellation (Optional)
                </label>
                <textarea
                  value={cancelModal.comments}
                  onChange={(e) => setCancelModal(prev => ({ ...prev, comments: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                  rows="3"
                  placeholder="Optional reason for cancelling..."
                />
              </div>
              <div className="flex items-center justify-end space-x-3">
                <button
                  onClick={() => setCancelModal({ open: false, request: null, comments: '', loading: false })}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                  disabled={cancelModal.loading}
                >
                  Keep Request
                </button>
                <button
                  onClick={handleCancelRequest}
                  disabled={cancelModal.loading}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {cancelModal.loading ? 'Cancelling...' : 'Cancel Request'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default LeaveHistory;