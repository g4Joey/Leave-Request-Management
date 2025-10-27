import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';

function HRApprovals() {
  const { user } = useAuth();
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [actionModal, setActionModal] = useState({ open: false, action: '', comments: '' });
  const [groupedApprovals, setGroupedApprovals] = useState({});

  useEffect(() => {
    fetchPendingApprovals();
  }, []);

  const fetchPendingApprovals = async () => {
    try {
      setLoading(true);
      const response = await api.get('/leaves/manager/pending_approvals/');
      const requests = response.data.requests || [];
      setPendingApprovals(requests);
      
      // Group requests by affiliate
      const grouped = requests.reduce((acc, request) => {
        const affiliate = getEmployeeAffiliate(request);
        if (!acc[affiliate]) {
          acc[affiliate] = [];
        }
        acc[affiliate].push(request);
        return acc;
      }, {});
      
      setGroupedApprovals(grouped);
    } catch (error) {
      console.error('Error fetching pending approvals:', error);
    } finally {
      setLoading(false);
    }
  };

  const getEmployeeAffiliate = (request) => {
    // Extract affiliate information from request
    if (request.employee_department_affiliate) {
      return request.employee_department_affiliate;
    }
    // Default grouping
    return 'Other';
  };

  const handleAction = async (requestId, action, comments = '') => {
    try {
      if (action === 'approve') {
        await api.put(`/leaves/manager/${requestId}/approve/`, {
          approval_comments: comments
        });
      } else if (action === 'reject') {
        await api.put(`/leaves/manager/${requestId}/reject/`, {
          rejection_comments: comments
        });
      }
      
      // Refresh the list
      await fetchPendingApprovals();
      setActionModal({ open: false, action: '', comments: '' });
      setSelectedRequest(null);
    } catch (error) {
      console.error(`Error ${action}ing request:`, error);
    }
  };

  const openActionModal = (request, action) => {
    setSelectedRequest(request);
    setActionModal({ open: true, action, comments: '' });
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      'pending': { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Pending Manager' },
      'manager_approved': { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Pending HR' },
      'hr_approved': { bg: 'bg-purple-100', text: 'text-purple-800', label: 'Pending CEO' },
    };
    
    const config = statusConfig[status] || { bg: 'bg-gray-100', text: 'text-gray-800', label: status };
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
        {config.label}
      </span>
    );
  };



  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h1 className="text-2xl font-semibold text-gray-900 mb-4">HR Approvals</h1>
          <p className="text-gray-600 mb-6">
            Review and process leave requests that require HR approval. These requests have been approved by managers and are awaiting your decision.
          </p>

          {pendingApprovals.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-gray-400 text-lg mb-2">📋</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No pending approvals</h3>
              <p className="text-gray-500">All leave requests are currently processed.</p>
            </div>
          ) : (
            <div className="space-y-8">
              {Object.entries(groupedApprovals).map(([affiliate, requests]) => (
                <div key={affiliate} className="space-y-4">
                  <div className="border-l-4 border-primary-500 pl-4">
                    <h2 className="text-xl font-semibold text-gray-900 mb-1">{affiliate}</h2>
                    <p className="text-sm text-gray-600">{requests.length} request{requests.length !== 1 ? 's' : ''} pending approval</p>
                  </div>
                  
                  <div className="space-y-4">
                    {requests.map((request) => (
                      <div key={request.id} className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow bg-white">
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex-1">
                            <h3 className="text-lg font-medium text-gray-900">
                              {request.employee_name || 'Employee'}
                            </h3>
                            <p className="text-sm text-gray-600">
                              {request.employee_department} • {getEmployeeAffiliate(request)}
                            </p>
                            <p className="text-sm text-gray-500 mt-1">
                              Employee ID: {request.employee_id || 'N/A'}
                            </p>
                          </div>
                          <div className="text-right">
                            {getStatusBadge(request.status)}
                          </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700">Leave Type</label>
                            <p className="mt-1 text-sm text-gray-900">{request.leave_type_name}</p>
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700">Duration</label>
                            <p className="mt-1 text-sm text-gray-900">
                              {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()}
                              <span className="ml-2 text-gray-500">({request.total_days} days)</span>
                            </p>
                          </div>
                        </div>

                        {request.reason && (
                          <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700">Reason</label>
                            <p className="mt-1 text-sm text-gray-900 bg-gray-50 p-3 rounded-md">{request.reason}</p>
                          </div>
                        )}

                        {request.manager_approval_comments && (
                          <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700">Manager's Comments</label>
                            <p className="mt-1 text-sm text-gray-900 bg-green-50 p-3 rounded-md border-l-4 border-green-400">
                              {request.manager_approval_comments}
                            </p>
                          </div>
                        )}

                        <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-200">
                          <button
                            onClick={() => openActionModal(request, 'reject')}
                            className="px-4 py-2 border border-red-300 text-red-700 rounded-md hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500"
                          >
                            Reject
                          </button>
                          <button
                            onClick={() => openActionModal(request, 'approve')}
                            className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
                          >
                            Approve
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Action Modal */}
      {actionModal.open && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                {actionModal.action === 'approve' ? 'Approve' : 'Reject'} Leave Request
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                {selectedRequest ? 
                  `${actionModal.action === 'approve' ? 'Approving' : 'Rejecting'} leave request for ${selectedRequest.employee_name}` :
                  ''
                }
              </p>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Comments {actionModal.action === 'reject' ? '(Required)' : '(Optional)'}
                </label>
                <textarea
                  value={actionModal.comments}
                  onChange={(e) => setActionModal(prev => ({ ...prev, comments: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  rows="3"
                  placeholder={`${actionModal.action === 'approve' ? 'Optional approval' : 'Required rejection'} comments...`}
                />
              </div>
              <div className="flex items-center justify-end space-x-3">
                <button
                  onClick={() => setActionModal({ open: false, action: '', comments: '' })}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleAction(selectedRequest?.id, actionModal.action, actionModal.comments)}
                  disabled={actionModal.action === 'reject' && !actionModal.comments.trim()}
                  className={`px-4 py-2 rounded-md ${
                    actionModal.action === 'approve'
                      ? 'bg-primary-600 hover:bg-primary-700 text-white'
                      : 'bg-red-600 hover:bg-red-700 text-white'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {actionModal.action === 'approve' ? 'Approve' : 'Reject'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default HRApprovals;