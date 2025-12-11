import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import api from '../services/api';
import OverlapAdvisory from './OverlapAdvisory';
import { emitApprovalChanged } from '../utils/approvalEvents';

function HRApprovals() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [actionModal, setActionModal] = useState({ open: false, action: '', comments: '' });
  const [groups, setGroups] = useState({ 'Merban Capital': [], 'SDSL': [], 'SBL': [] });
  const [activeAffiliate, setActiveAffiliate] = useState('Merban Capital');
  
  // Approval Records state
  const [approvalRecords, setApprovalRecords] = useState([]);
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [recordsSearch, setRecordsSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [recordsPage, setRecordsPage] = useState(0);
  const [recordsHasMore, setRecordsHasMore] = useState(false);
  const PAGE_SIZE = 20;
  const [expandedRecordIds, setExpandedRecordIds] = useState(new Set());

  useEffect(() => {
    fetchPendingApprovals();
    fetchApprovalRecords();
  }, []);

  const fetchApprovalRecords = useCallback(async (page = 0, search = recordsSearch, status = statusFilter) => {
    try {
      setRecordsLoading(true);
      const params = {
        ordering: '-created_at',
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        search: search || undefined,
        status: status || undefined
      };
      
      const response = await api.get('/leaves/manager/recent_activity/', { params });
      const data = response.data;
      const items = data.results || data || [];
      
      setApprovalRecords(items);
      setRecordsPage(page);
      setRecordsHasMore(data && typeof data === 'object' && 'next' in data ? Boolean(data.next) : items.length === PAGE_SIZE);
    } catch (error) {
      console.error('Error fetching approval records:', error);
      setApprovalRecords([]);
      setRecordsHasMore(false);
    } finally {
      setRecordsLoading(false);
    }
  }, [recordsSearch, statusFilter, PAGE_SIZE]);

  const fetchPendingApprovals = async () => {
    try {
      setLoading(true);
      const response = await api.get('/leaves/manager/hr_approvals_categorized/');
      const data = response.data || {};
      const incoming = data.groups || {};
      if (process.env.NODE_ENV === 'development') {
        // Debug logging to inspect backend payload vs UI state
        console.log('[HRApprovals] Raw response:', response.data);
        console.log('[HRApprovals] Incoming groups keys:', Object.keys(incoming));
        console.log('[HRApprovals] Counts:', data.counts, 'Total:', data.total);
      }
      const normalized = {
        'Merban Capital': incoming['Merban Capital'] || [],
        'SDSL': incoming['SDSL'] || [],
        'SBL': incoming['SBL'] || []
      };
      setGroups(normalized);
      const firstWithItems = Object.keys(normalized).find(k => normalized[k].length > 0) || 'Merban Capital';
      setActiveAffiliate(firstWithItems);
    } catch (error) {
      console.error('Error fetching HR categorized approvals:', error);
    } finally {
      setLoading(false);
    }
  };

  const getEmployeeAffiliate = (request) => {
    const aff = (request.employee_department_affiliate || request.employee_affiliate || '').toString().trim();
    if (/^merban(\s+capital)?$/i.test(aff)) return 'Merban Capital';
    if (/^SDSL$/i.test(aff)) return 'SDSL';
    if (/^SBL$/i.test(aff)) return 'SBL';
    return aff || 'Other';
  };

  const handleAction = async (request, action, comments = '') => {
    try {
      const isInterrupt = request?._is_interrupt || request?.is_interrupt || request?.isInterrupt;
      if (isInterrupt) {
        const interruptId = request?.id;
        const endpoint = action === 'approve' ? 'hr-approve' : 'hr-reject';
        await api.post(`/leaves/manager/interrupts/${interruptId}/${endpoint}/`, { reason: comments || '' });
      } else if (action === 'approve') {
        await api.put(`/leaves/manager/${request.id}/approve/`, { approval_comments: comments || '' });
      } else if (action === 'reject') {
        await api.put(`/leaves/manager/${request.id}/reject/`, { approval_comments: comments || '' });
      }
      await fetchPendingApprovals();
      emitApprovalChanged();
      setActionModal({ open: false, action: '', comments: '' });
      setSelectedRequest(null);
      const verb = action === 'approve' ? 'approved' : 'rejected';
      showToast({ type: 'success', message: `Request ${verb} successfully.` });
    } catch (error) {
      console.error(`Error ${action}ing request:`, error);
      const detail = error?.response?.data?.error || error?.response?.data?.detail || '';
      showToast({ type: 'error', message: `Failed to ${action} request${detail ? `: ${detail}` : ''}` });
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

  const getDynamicStatusBadge = (request) => {
    // Use backend's dynamic status display if available
    const displayText = request.status_display || request.status;
    
    // Color coding based on status keywords
    let badgeClass = 'bg-gray-100 text-gray-800';
    if (displayText.includes('Pending Manager') || displayText.includes('Pending CEO')) {
      badgeClass = 'bg-yellow-100 text-yellow-800';
    } else if (displayText.includes('Pending HR')) {
      badgeClass = 'bg-blue-100 text-blue-800';
    } else if (displayText.includes('Manager Approved') || displayText.includes('CEO Approved')) {
      badgeClass = 'bg-blue-100 text-blue-800';
    } else if (displayText.includes('HR Approved')) {
      badgeClass = 'bg-purple-100 text-purple-800';
    } else if (displayText === 'Approved') {
      badgeClass = 'bg-green-100 text-green-800';
    } else if (displayText === 'Rejected') {
      badgeClass = 'bg-red-100 text-red-800';
    }
    
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${badgeClass}`}>
        {displayText}
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

          <div className="space-y-6">
            <div className="border-b border-gray-200">
              <nav className="flex space-x-8 px-2" aria-label="Tabs">
                {['Merban Capital','SDSL','SBL'].map(key => {
                  const count = groups[key].length;
                  return (
                    <button
                      key={key}
                      onClick={() => setActiveAffiliate(key)}
                      className={`py-4 px-1 border-b-2 font-medium text-sm whitespace-nowrap`}
                      style={activeAffiliate === key ? { borderBottomColor: 'var(--primary)', color: 'var(--primary)' } : {}}
                    >
                      {key}
                      <span className={`ml-2 py-0.5 px-2 rounded-full text-xs`} style={activeAffiliate === key ? { backgroundColor: 'var(--primary)', color: 'var(--on-primary)' } : { backgroundColor: '#f3f4f6', color: '#111827' }}>{count}</span>
                    </button>
                  );
                })}
              </nav>
            </div>

            <div className="space-y-4">
              {['Merban Capital','SDSL','SBL'].map((key) => (
                <div key={key} className={activeAffiliate === key ? 'block' : 'hidden'}>
                  {groups[key].length === 0 ? (
                    <div className="text-center py-12">
                      <svg className="mx-auto h-12 w-12 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <h3 className="text-lg font-medium text-gray-900 mt-4">No pending approvals</h3>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {groups[key].map((request) => {
                        const isInterrupt = request._is_interrupt || request.is_interrupt || request.isInterrupt;
                        if (isInterrupt) {
                          return (
                            <div key={`interrupt-${request.id}`} className="border border-amber-200 rounded-lg p-6 hover:shadow-md transition-shadow bg-amber-50 border-l-4 border-amber-400">
                              <div className="flex items-start justify-between mb-3">
                                <div className="flex-1">
                                  <h3 className="text-lg font-medium text-gray-900 flex items-center gap-2">
                                    {request.employee_name || 'Employee'}
                                    <span className="text-amber-800 text-xs px-2 py-0.5 rounded-full bg-amber-200">Early return</span>
                                  </h3>
                                  <p className="text-sm text-gray-600">{request.leave_type_name}</p>
                                  <p className="text-sm text-gray-500">{new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()} ({request.total_days} working days)</p>
                                  <p className="text-sm text-amber-800 mt-1">Requested resume: {new Date(request.requested_resume_date).toLocaleDateString()}</p>
                                </div>
                                <div className="text-right">{getDynamicStatusBadge({ status_display: 'Pending HR' })}</div>
                              </div>
                              {request.reason && (
                                <div className="mb-4 text-sm text-gray-900 bg-white p-3 rounded-md border border-amber-100">
                                  <strong>Reason:</strong> {request.reason}
                                </div>
                              )}
                              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-amber-200">
                                <button onClick={() => openActionModal(request, 'reject')} className="px-4 py-2 border border-red-300 text-red-700 rounded-md hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500">Reject</button>
                                <button onClick={() => openActionModal(request, 'approve')} className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500">Approve</button>
                              </div>
                            </div>
                          );
                        }

                        return (
                          <div key={request.id} className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow bg-white">
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
                                <h3 className="text-lg font-medium text-gray-900">{request.employee_name || 'Employee'}</h3>
                                <p className="text-sm text-gray-600">{request.employee_department} • {getEmployeeAffiliate(request)}</p>
                                <p className="text-sm text-gray-500 mt-1">Employee ID: {request.employee_id || 'N/A'}</p>
                              </div>
                              <div className="text-right">{getDynamicStatusBadge(request)}</div>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                              <div>
                                <label className="block text-sm font-medium text-gray-700">Leave Type</label>
                                <p className="mt-1 text-sm text-gray-900">{request.leave_type_name}</p>
                              </div>
                              <div>
                                <label className="block text-sm font-medium text-gray-700">Duration</label>
                                <p className="mt-1 text-sm text-gray-900">{new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()}<span className="ml-2 text-gray-500">({request.total_days} days)</span></p>
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
                                <p className="mt-1 text-sm text-gray-900 bg-green-50 p-3 rounded-md border-l-4 border-green-400">{request.manager_approval_comments}</p>
                              </div>
                            )}
                            <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-200">
                              <button onClick={() => openActionModal(request, 'reject')} className="px-4 py-2 border border-red-300 text-red-700 rounded-md hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500">Reject</button>
                              <button onClick={() => openActionModal(request, 'approve')} className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500">Approve</button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Approval Records Section */}
      <div className="bg-white shadow rounded-lg mt-6">
        <div className="px-4 py-5 sm:p-6">
          <h4 className="text-md leading-6 font-semibold text-gray-900 mb-4">Approval Records</h4>
          <p className="text-sm text-gray-600 mb-4">Recent requests you have approved or rejected</p>
          
          {/* Search and Filter Controls */}
          <div className="mb-4 flex flex-col sm:flex-row gap-3">
            <div className="flex-1">
              <input
                type="text"
                placeholder="Search by employee name..."
                value={recordsSearch}
                onChange={(e) => setRecordsSearch(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    setRecordsPage(0);
                    fetchApprovalRecords(0, recordsSearch, statusFilter);
                  }
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              />
            </div>
            <div className="sm:w-48">
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setRecordsPage(0);
                  fetchApprovalRecords(0, recordsSearch, e.target.value);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              >
                <option value="">All Statuses</option>
                <option value="approved">Approved Only</option>
                <option value="rejected">Rejected Only</option>
              </select>
            </div>
            <button
              onClick={() => {
                setRecordsPage(0);
                fetchApprovalRecords(0, recordsSearch, statusFilter);
              }}
              className="px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              Search
            </button>
            {(recordsSearch || statusFilter) && (
              <button
                onClick={() => {
                  setRecordsSearch('');
                  setStatusFilter('');
                  setRecordsPage(0);
                  fetchApprovalRecords(0, '', '');
                }}
                className="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                Clear
              </button>
            )}
          </div>
          
          {recordsLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500 mx-auto"></div>
            </div>
          ) : approvalRecords.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-sm text-gray-500">No approval records found</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {approvalRecords.map((record) => {
                const isApproved = record.status === 'approved';
                const statusColor = isApproved 
                  ? 'bg-green-100 text-green-800 ring-green-200' 
                  : 'bg-red-100 text-red-800 ring-red-200';

                return (
                  <button
                    key={`record-${record.id}`}
                    className="w-full py-3 text-left"
                    onClick={() => {
                      const next = new Set(expandedRecordIds);
                      const key = record.id;
                      if (next.has(key)) next.delete(key); else next.add(key);
                      setExpandedRecordIds(next);
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{record.employee_name || 'Employee'} — {record.leave_type_name}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(record.start_date).toLocaleDateString()} - {new Date(record.end_date).toLocaleDateString()} 
                          <span className="ml-1">({record.total_days} working days)</span>
                        </p>
                      </div>
                      <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${statusColor} ml-4`}>
                        {isApproved ? 'Approved' : 'Rejected'}
                      </span>
                    </div>
                    {expandedRecordIds.has(record.id) && (
                      <div className="mt-3 space-y-2 text-xs text-gray-700">
                        {record.reason && <div><strong>Reason:</strong> {record.reason}</div>}
                        {record.hr_comments && <div><strong>HR Comments:</strong> {record.hr_comments}</div>}
                        <div className="text-gray-500">Submitted: {new Date(record.created_at).toLocaleString()}</div>
                        {record.timeline_events && record.timeline_events.length > 0 && (
                          <div className="space-y-1">
                            {record.timeline_events.map((ev, idx) => (
                              <div key={idx} className="flex items-start gap-2">
                                <span className="text-gray-400">•</span>
                                <div>
                                  <div className="font-semibold">{(ev.is_self ? 'You' : (ev.actor_name || 'Someone')) + ' ' + ((ev.action || '').replace(/_/g, ' '))}</div>
                                  <div className="text-gray-500">{new Date(ev.timestamp).toLocaleString()}</div>
                                  {ev.note ? <div className="text-gray-600">{ev.note}</div> : null}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          )}
          
          {/* Pagination Controls */}
          {approvalRecords.length > 0 && (
            <div className="mt-4 flex items-center justify-between border-t border-gray-200 pt-4">
              <div className="flex-1 flex justify-between sm:hidden">
                <button
                  onClick={() => {
                    const newPage = Math.max(0, recordsPage - 1);
                    fetchApprovalRecords(newPage, recordsSearch, statusFilter);
                  }}
                  disabled={recordsPage === 0}
                  className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => {
                    fetchApprovalRecords(recordsPage + 1, recordsSearch, statusFilter);
                  }}
                  disabled={!recordsHasMore}
                  className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
              <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-gray-700">
                    Showing page <span className="font-medium">{recordsPage + 1}</span>
                  </p>
                </div>
                <div>
                  <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                    <button
                      onClick={() => {
                        const newPage = Math.max(0, recordsPage - 1);
                        fetchApprovalRecords(newPage, recordsSearch, statusFilter);
                      }}
                      disabled={recordsPage === 0}
                      className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => {
                        fetchApprovalRecords(recordsPage + 1, recordsSearch, statusFilter);
                      }}
                      disabled={!recordsHasMore}
                      className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                  </nav>
                </div>
              </div>
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
                  onClick={() => handleAction(selectedRequest, actionModal.action, actionModal.comments)}
                  disabled={actionModal.action === 'reject' && !actionModal.comments.trim()}
                  className={`px-4 py-2 rounded-md ${actionModal.action === 'approve' ? 'bg-primary-600 hover:bg-primary-700 text-white' : 'bg-red-600 hover:bg-red-700 text-white'} disabled:opacity-50 disabled:cursor-not-allowed`}
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