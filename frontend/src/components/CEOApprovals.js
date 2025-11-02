import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { Dialog } from '@headlessui/react';
import { useToast } from '../contexts/ToastContext';
import OverlapAdvisory from './OverlapAdvisory';

function CEOApprovals() {
  const { showToast } = useToast();
  const [requests, setRequests] = useState({
    hod_manager: [],
    hr: [],
    staff: []
  });
  const [loading, setLoading] = useState(true);
  const [loadingActionById, setLoadingActionById] = useState({});
  const [rejectModal, setRejectModal] = useState({ open: false, requestId: null, reason: '' });
  const [activeTab, setActiveTab] = useState('hod_manager');

  const fetchCEORequests = useCallback(async () => {
    try {
      setLoading(true);
      // Get categorized pending requests for CEO approval
      const response = await api.get('/leaves/manager/ceo_approvals_categorized/');
      
      setRequests(response.data.categories || {
        hod_manager: [],
        hr: [],
        staff: []
      });
    } catch (error) {
      console.error('Error fetching CEO requests:', error);
      showToast({ type: 'error', message: 'Failed to load approval requests' });
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    fetchCEORequests();
  }, [fetchCEORequests]);

  const handleAction = async (requestId, action, comments = '') => {
    setLoadingActionById(prev => ({ ...prev, [requestId]: action }));

    try {
      await api.put(`/leaves/manager/${requestId}/${action}/`, {
        approval_comments: comments || ''
      });
      
      // Remove from all categories and refresh
      setRequests(prev => ({
        hod_manager: prev.hod_manager.filter(req => req.id !== requestId),
        hr: prev.hr.filter(req => req.id !== requestId),
        staff: prev.staff.filter(req => req.id !== requestId)
      }));
      
      showToast({ 
        type: 'success', 
        message: `Request ${action}ed successfully as CEO.` 
      });
    } catch (error) {
      console.error(`Error ${action}ing request:`, error);
      const detail = error?.response?.data?.error || error?.response?.data?.detail || '';
      showToast({ 
        type: 'error', 
        message: `Failed to ${action} request${detail ? `: ${detail}` : ''}` 
      });
    } finally {
      setLoadingActionById(prev => ({ ...prev, [requestId]: undefined }));
    }
  };

  const handleReject = (requestId) => {
    setRejectModal({ open: true, requestId, reason: '' });
  };

  const confirmReject = async () => {
    if (!rejectModal.reason.trim()) {
      showToast({ type: 'error', message: 'Please provide a reason for rejection' });
      return;
    }
    
    await handleAction(rejectModal.requestId, 'reject', rejectModal.reason);
    setRejectModal({ open: false, requestId: null, reason: '' });
  };

  const getEmployeeName = (request) => {
    return request?.employee_name || request?.employee_email || 'Unknown Employee';
  };

  const getEmployeeDepartment = (request) => {
    return request?.employee_department || 'Unknown Department';
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString();
  };

  const calculateDuration = (startDate, endDate) => {
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = Math.abs(end - start);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
    return diffDays;
  };

  const RequestCard = ({ request, categoryType }) => {
    const isApproving = loadingActionById[request.id] === 'approve';
    const isRejecting = loadingActionById[request.id] === 'reject';
    const duration = calculateDuration(request.start_date, request.end_date);

    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
        {/* Overlap Advisory Banner */}
        <OverlapAdvisory 
          leaveRequest={{
            ...request,
            employee_department_id: request.employee_department_id || request.department_id,
            employee_id: request.employee_id || request.employee
          }}
          className="mb-4"
        />
        
        <div className="flex justify-between items-start mb-4">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900">
              {getEmployeeName(request)}
            </h3>
            <div className="text-sm text-gray-600 space-y-1 mt-2">
              <p><span className="font-medium">Department:</span> {getEmployeeDepartment(request)}</p>
              <p><span className="font-medium">Employee ID:</span> {request.employee_id || 'N/A'}</p>
              <p><span className="font-medium">Role:</span> 
                <span className={`ml-1 px-2 py-1 rounded-full text-xs font-medium ${
                  categoryType === 'hod_manager' ? 'bg-purple-100 text-purple-800' :
                  categoryType === 'hr' ? 'bg-blue-100 text-blue-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {categoryType === 'hod_manager' ? 'HOD/Manager' : 
                   categoryType === 'hr' ? 'HR Staff' : 'Staff Member'}
                </span>
              </p>
            </div>
          </div>
        </div>

        <div className="border-t border-gray-100 pt-4">
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <p className="text-sm font-medium text-gray-700">Leave Type</p>
              <p className="text-sm text-gray-900">{request.leave_type_name || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-700">Duration</p>
              <p className="text-sm text-gray-900">{duration} day{duration !== 1 ? 's' : ''}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-700">Start Date</p>
              <p className="text-sm text-gray-900">{formatDate(request.start_date)}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-700">End Date</p>
              <p className="text-sm text-gray-900">{formatDate(request.end_date)}</p>
            </div>
          </div>

          {request.reason && (
            <div className="mb-4">
              <p className="text-sm font-medium text-gray-700">Reason</p>
              <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">{request.reason}</p>
            </div>
          )}

          {request.manager_comments && (
            <div className="mb-4">
              <p className="text-sm font-medium text-gray-700">Manager Comments</p>
              <p className="text-sm text-gray-900 bg-blue-50 p-2 rounded">{request.manager_comments}</p>
            </div>
          )}

          {request.hr_comments && (
            <div className="mb-4">
              <p className="text-sm font-medium text-gray-700">HR Comments</p>
              <p className="text-sm text-gray-900 bg-green-50 p-2 rounded">{request.hr_comments}</p>
            </div>
          )}

          <div className="flex space-x-3 pt-4">
            <button
              onClick={() => handleAction(request.id, 'approve')}
              disabled={isApproving || isRejecting}
              className="flex-1 bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 
                       disabled:opacity-50 disabled:cursor-not-allowed transition-colors
                       flex items-center justify-center"
            >
              {isApproving ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Approving...
                </>
              ) : (
                'Final Approve'
              )}
            </button>
            <button
              onClick={() => handleReject(request.id)}
              disabled={isApproving || isRejecting}
              className="flex-1 bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 
                       disabled:opacity-50 disabled:cursor-not-allowed transition-colors
                       flex items-center justify-center"
            >
              {isRejecting ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Rejecting...
                </>
              ) : (
                'Reject'
              )}
            </button>
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  const tabs = [
    { 
      key: 'hod_manager', 
      label: 'HOD/Manager Requests', 
      count: requests.hod_manager.length,
      description: 'Leave requests from department heads and managers'
    },
    { 
      key: 'hr', 
      label: 'HR Requests', 
      count: requests.hr.length,
      description: 'Leave requests from HR staff members'
    },
    { 
      key: 'staff', 
      label: 'Staff Requests', 
      count: requests.staff.length,
      description: 'Leave requests from regular staff members'
    }
  ];

  const totalPending = requests.hod_manager.length + requests.hr.length + requests.staff.length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white overflow-hidden shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-2">
            CEO Approvals Portal
          </h3>
          <p className="text-sm text-gray-600">
            Review and approve leave requests requiring final CEO authorization.
          </p>
          <div className="mt-4">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
              {totalPending} Pending Final Approval{totalPending !== 1 ? 's' : ''}
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
              
              {requests[tab.key].length === 0 ? (
                <div className="text-center py-12">
                  <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No pending approvals</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    All {tab.label.toLowerCase()} have been processed.
                  </p>
                </div>
              ) : (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
                  {requests[tab.key].map((request) => (
                    <RequestCard 
                      key={request.id} 
                      request={request} 
                      categoryType={tab.key}
                    />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Reject Modal */}
      <Dialog open={rejectModal.open} onClose={() => setRejectModal({ open: false, requestId: null, reason: '' })}>
        <div className="fixed inset-0 bg-black bg-opacity-25" />
        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
              <Dialog.Title as="h3" className="text-lg font-medium leading-6 text-gray-900">
                Reject Leave Request
              </Dialog.Title>
              <div className="mt-2">
                <p className="text-sm text-gray-500">
                  Please provide a reason for rejecting this leave request.
                </p>
              </div>
              <div className="mt-4">
                <textarea
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  rows={4}
                  placeholder="Enter rejection reason..."
                  value={rejectModal.reason}
                  onChange={(e) => setRejectModal(prev => ({ ...prev, reason: e.target.value }))}
                />
              </div>
              <div className="mt-4 flex space-x-3">
                <button
                  type="button"
                  className="flex-1 inline-flex justify-center rounded-md border border-transparent bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
                  onClick={confirmReject}
                  disabled={!rejectModal.reason.trim()}
                >
                  Confirm Rejection
                </button>
                <button
                  type="button"
                  className="flex-1 inline-flex justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
                  onClick={() => setRejectModal({ open: false, requestId: null, reason: '' })}
                >
                  Cancel
                </button>
              </div>
            </Dialog.Panel>
          </div>
        </div>
      </Dialog>
    </div>
  );
}

export default CEOApprovals;