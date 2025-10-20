import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';

function CEOApprovals() {
  const { showToast } = useToast();
  const [requests, setRequests] = useState({
    hod_manager: [],
    hr: [],
    staff: []
  });
  const [loading, setLoading] = useState(true);

  const [activeTab, setActiveTab] = useState('hod_manager');

  const fetchCEORequests = useCallback(async () => {
    try {
      setLoading(true);
      // Get processed requests that CEO has already acted upon
      const response = await api.get('/leaves/requests/?limit=50');
      const allRequests = response.data.results || response.data || [];
      
      // Filter for requests that CEO has already processed
      const processedRequests = allRequests.filter(request => 
        (request.status === 'approved' && request.ceo_approval_date) ||
        (request.status === 'rejected' && request.ceo_approval_date)
      );
      
      // Categorize by employee role
      const categorized = {
        hod_manager: processedRequests.filter(req => req.employee_role === 'manager'),
        hr: processedRequests.filter(req => req.employee_role === 'hr'),
        staff: processedRequests.filter(req => ['junior_staff', 'senior_staff'].includes(req.employee_role))
      };
      
      setRequests(categorized);
    } catch (error) {
      console.error('Error fetching CEO requests:', error);
      showToast({ type: 'error', message: 'Failed to load processed requests' });
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    fetchCEORequests();
  }, [fetchCEORequests]);



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
    const duration = calculateDuration(request.start_date, request.end_date);

    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
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

          {/* Status and processing info */}
          <div className="flex justify-between items-center pt-4 border-t border-gray-100">
            <div className="flex items-center space-x-4">
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                request.status === 'approved' 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-red-100 text-red-800'
              }`}>
                {request.status === 'approved' ? 'Approved by CEO' : 'Rejected by CEO'}
              </span>
              {request.ceo_approval_date && (
                <span className="text-xs text-gray-500">
                  Processed: {formatDate(request.ceo_approval_date)}
                </span>
              )}
            </div>
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

  const totalProcessed = requests.hod_manager.length + requests.hr.length + requests.staff.length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white overflow-hidden shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-2">
            CEO Dashboard
          </h3>
          <p className="text-sm text-gray-600">
            View your recently processed leave requests and approval decisions.
          </p>
          <div className="mt-4">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
              {totalProcessed} Processed Request{totalProcessed !== 1 ? 's' : ''}
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


    </div>
  );
}

export default CEOApprovals;