import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import api from '../services/api';
import OverlapAdvisory from './OverlapAdvisory';

function HRApprovals() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [actionModal, setActionModal] = useState({ open: false, action: '', comments: '' });
  const [actingId, setActingId] = useState(null);
  const [groupedApprovals, setGroupedApprovals] = useState({});
  const [activeTab, setActiveTab] = useState('Merban Capital');

  useEffect(() => {
    fetchPendingApprovals();
  }, []);

  const fetchPendingApprovals = async () => {
    try {
      setLoading(true);
    // Fetch HR pending approvals via manager endpoint action (stage-aware server filtering)
    // Use stage=hr so admin/superuser can also view the HR queue
    const response = await api.get('/leaves/manager/pending_approvals/?stage=hr');
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
  // Auto-select first tab that has items
  const orderedKeys = ['Merban Capital', 'SDSL', 'SBL'];
  const firstWithItems = orderedKeys.find(k => (grouped[k] || []).length > 0);
  if (firstWithItems) setActiveTab(firstWithItems);
    } catch (error) {
      console.error('Error fetching pending approvals:', error);
    } finally {
      setLoading(false);
    }
  };

  const getEmployeeAffiliate = (request) => {
    // Extract affiliate information from request and normalize to tab keys
    const raw = request.employee_department_affiliate || request.employee_affiliate || request.affiliate || '';
    const name = (raw || '').toString().trim();
    if (!name) return 'Other';
    // Normalize common variants/casing
    if (/^merban(\s+capital)?$/i.test(name) || /^merban\s*capital$/i.test(name) || name.toUpperCase() === 'MERBAN CAPITAL') {
      return 'Merban Capital';
    }
    if (name.toUpperCase() === 'SDSL') return 'SDSL';
    if (name.toUpperCase() === 'SBL') return 'SBL';
    return name; // fallback: show as-is
  };

  const handleAction = async (requestId, action, comments = '') => {
    try {
      setActingId(requestId);
      if (action === 'approve') {
        // Approver endpoints live under /leaves/manager/
        await api.put(`/leaves/manager/${requestId}/approve/`, {
          approval_comments: comments
        });
        showToast({ 
          type: 'success', 
          message: 'Leave request approved successfully by HR.' 
        });
      } else if (action === 'reject') {
        await api.put(`/leaves/manager/${requestId}/reject/`, {
          rejection_comments: comments
        });
        showToast({ 
          type: 'success', 
          message: 'Leave request rejected successfully.' 
        });
      }
      
      // Refresh the list
      await fetchPendingApprovals();
      setActionModal({ open: false, action: '', comments: '' });
      setSelectedRequest(null);
    } catch (error) {
      console.error(`Error ${action}ing request:`, error);
      const detail = error?.response?.data?.error || error?.response?.data?.detail || '';
      showToast({ 
        type: 'error', 
        message: `Failed to ${action} request${detail ? `: ${detail}` : ''}` 
      });
    }
    finally {
      setActingId(null);
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
      // CEO-first (SDSL/SBL) flow where HR is final approver
      'ceo_approved': { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Pending HR' },
      'hr_approved': { bg: 'bg-purple-100', text: 'text-purple-800', label: 'Pending CEO' },
    };
    
    const config = statusConfig[status] || { bg: 'bg-gray-100', text: 'text-gray-800', label: status };
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
        {config.label}
      </span>
    );
  };

  const tabs = [
    { key: 'Merban Capital', label: 'Merban Capital', count: (groupedApprovals['Merban Capital'] || []).length, description: 'Requests from Merban Capital employees pending HR review' },
    { key: 'SDSL', label: 'SDSL', count: (groupedApprovals['SDSL'] || []).length, description: 'Requests from SDSL employees pending HR review' },
    { key: 'SBL', label: 'SBL', count: (groupedApprovals['SBL'] || []).length, description: 'Requests from SBL employees pending HR review' },
  ];

  const totalPending = tabs.reduce((sum, t) => sum + t.count, 0);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white overflow-hidden shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-2">
            HR Approvals
          </h3>
          <p className="text-sm text-gray-600">
            Review and process leave requests that require HR approval. These requests have been approved by managers and are awaiting your decision.
          </p>
          <div className="mt-4">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
              {totalPending} Pending HR Approval{totalPending !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6" aria-label="Tabs">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`py-4 px-1 border-b-2 font-medium text-sm whitespace-nowrap ${
                  activeTab === tab.key
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
                {tab.count > 0 && (
                  <span className={`ml-2 py-0.5 px-2 rounded-full text-xs ${
                    activeTab === tab.key 
                      ? 'bg-primary-100 text-primary-600' 
                      : 'bg-gray-100 text-gray-900'
                  }`}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {tabs.map((tab) => (
            <div key={tab.key} className={activeTab === tab.key ? 'block' : 'hidden'}>
              <div className="mb-4">
                <p className="text-sm text-gray-600">{tab.description}</p>
              </div>

              {(groupedApprovals[tab.key] || []).length === 0 ? (
                <div className="text-center py-12">
                  <div className="text-gray-400 text-lg mb-2">📋</div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No pending approvals</h3>
                  <p className="text-gray-500">All {tab.label} requests are currently processed.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {(groupedApprovals[tab.key] || []).map((request) => (
                    <div key={request.id} className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow bg-white">
                      {/* Overlap Advisory Banner */}
                      <OverlapAdvisory 
                        leaveRequest={{
                          ...request,
                          employee_department_id: request.employee_department_id || request.department_id,
                          employee_id: request.employee_id || request.employee
                        }}
                        className="mb-4"
                      />

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
                          onClick={() => handleAction(request.id, 'approve')}
                          disabled={actingId === request.id}
                          className={`px-4 py-2 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500 ${actingId === request.id ? 'bg-primary-400 cursor-wait' : 'bg-primary-600 hover:bg-primary-700'}`}
                        >
                          {actingId === request.id ? 'Approving…' : 'Approve'}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
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
                  Comments (Optional)
                </label>
                <textarea
                  value={actionModal.comments}
                  onChange={(e) => setActionModal(prev => ({ ...prev, comments: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  rows="3"
                  placeholder={`Add ${actionModal.action === 'approve' ? 'approval' : 'rejection'} comments (optional)…`}
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