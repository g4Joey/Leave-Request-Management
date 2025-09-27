import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { Dialog } from '@headlessui/react';
import { useToast } from '../contexts/ToastContext';

function ManagerDashboard() {
  const { showToast } = useToast();
  const [pendingRequests, setPendingRequests] = useState([]);
  const [leaveRecords, setLeaveRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  // Track which action is loading per request id: 'approve' | 'reject' | undefined
  const [loadingActionById, setLoadingActionById] = useState({});
  const [rejectModal, setRejectModal] = useState({ open: false, requestId: null, reason: '' });
  const PAGE_SIZE = 15;
  // Pagination & filters for Leave Records (approved + rejected)
  const [recordsPage, setRecordsPage] = useState(0);
  const [recordsHasMore, setRecordsHasMore] = useState(false);
  const [recordsSearch, setRecordsSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState(''); // 'approved', 'rejected', or '' for all
  const [hasSearched, setHasSearched] = useState(false); // Track if user has performed a search
  

  const fetchLeaveRecords = useCallback(async (page = recordsPage, search = recordsSearch, status = statusFilter) => {
    try {
      let allItems = [];
      
      if (status) {
        // Fetch specific status
        const params = { 
          ordering: '-created_at', 
          limit: PAGE_SIZE, 
          offset: page * PAGE_SIZE,
          search: search || undefined,
          status: status
        };
        
        const res = await api.get('/leaves/manager/', { params });
        const data = res.data;
        allItems = data.results || data;
        
        setRecordsHasMore(data && typeof data === 'object' && 'next' in data ? Boolean(data.next) : allItems.length === PAGE_SIZE);
      } else {
        // Fetch both approved and rejected in parallel, then combine and sort
        const [approvedRes, rejectedRes] = await Promise.all([
          api.get('/leaves/manager/', { 
            params: { 
              ordering: '-created_at', 
              limit: Math.ceil(PAGE_SIZE / 2), 
              offset: Math.floor(page * PAGE_SIZE / 2),
              search: search || undefined,
              status: 'approved'
            }
          }),
          api.get('/leaves/manager/', { 
            params: { 
              ordering: '-created_at', 
              limit: Math.ceil(PAGE_SIZE / 2), 
              offset: Math.floor(page * PAGE_SIZE / 2),
              search: search || undefined,
              status: 'rejected'
            }
          })
        ]);
        
        const approvedItems = approvedRes.data.results || approvedRes.data;
        const rejectedItems = rejectedRes.data.results || rejectedRes.data;
        
        // Combine and sort by created_at descending
        allItems = [...approvedItems, ...rejectedItems].sort((a, b) => 
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        ).slice(0, PAGE_SIZE);
        
        // Check if there are more records
        const hasMoreApproved = approvedRes.data && typeof approvedRes.data === 'object' && 'next' in approvedRes.data ? Boolean(approvedRes.data.next) : false;
        const hasMoreRejected = rejectedRes.data && typeof rejectedRes.data === 'object' && 'next' in rejectedRes.data ? Boolean(rejectedRes.data.next) : false;
        setRecordsHasMore(hasMoreApproved || hasMoreRejected || allItems.length === PAGE_SIZE);
      }
      
      setLeaveRecords(allItems);
      setRecordsPage(page);
      setHasSearched(true);
    } catch (e) {
      console.error('Error fetching leave records:', e);
      // non-blocking - set empty array on error
      setLeaveRecords([]);
      setRecordsHasMore(false);
      setHasSearched(true);
    }
  }, [PAGE_SIZE, recordsPage, recordsSearch, statusFilter]);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [pendingRes] = await Promise.all([
          api.get('/leaves/manager/pending_approvals/'),
        ]);
        setPendingRequests(pendingRes.data.results || pendingRes.data);
        // Don't load leave records initially - only when user searches
      } catch (error) {
        console.error('Error fetching pending requests:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAll();
  }, []);

  const handleAction = async (requestId, action, comments = '') => {
    setLoadingActionById((prev) => ({ ...prev, [requestId]: action }));

    try {
      await api.put(`/leaves/manager/${requestId}/${action}/`, {
        approval_comments: comments || ''
      });
      
      // Remove the request from the pending list
      setPendingRequests(prev => prev.filter(req => req.id !== requestId));
      // Refresh leave records only if user has already searched
      if (hasSearched) {
        await fetchLeaveRecords(recordsPage, recordsSearch, statusFilter);
      }
      // Global toast and optional haptics
      showToast({ type: 'success', message: `Request ${action}ed successfully.` });
      if (navigator && 'vibrate' in navigator) {
        try { navigator.vibrate(40); } catch (_) { /* noop */ }
      }
    } catch (error) {
      console.error(`Error ${action}ing request:`, error);
      const detail = error?.response?.data?.error || error?.response?.data?.detail || '';
      showToast({ type: 'error', message: `Failed to ${action} request${detail ? `: ${detail}` : ''}` });
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
                          onClick={() => setRejectModal({ open: true, requestId: request.id, reason: '' })}
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

      {/* Leave Records Section (Approved & Rejected consolidated) */}
      <div className="px-4 py-5 sm:px-6">
        <h4 className="text-md leading-6 font-semibold text-gray-900">Leave Records</h4>
        <div className="mt-2 flex items-center gap-2 flex-wrap">
          <input
            type="text"
            placeholder="Search by employee name, leave type, or date"
            value={recordsSearch}
            onChange={(e) => setRecordsSearch(e.target.value)}
            className="flex-1 min-w-64 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
          >
            <option value="">All Status</option>
            <option value="approved">Approved Only</option>
            <option value="rejected">Rejected Only</option>
          </select>
          <button
            onClick={() => {
              setRecordsPage(0);
              fetchLeaveRecords(0, recordsSearch, statusFilter);
            }}
            className="px-3 py-2 rounded-md bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium"
          >
            Search
          </button>
          {hasSearched && (
            <button
              onClick={() => {
                setRecordsSearch('');
                setStatusFilter('');
                setLeaveRecords([]);
                setHasSearched(false);
                setRecordsPage(0);
                setRecordsHasMore(false);
              }}
              className="px-3 py-2 rounded-md bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium"
            >
              Clear
            </button>
          )}
        </div>
      </div>
      <ul className="divide-y divide-gray-200">
        {leaveRecords.length > 0 ? (
          leaveRecords.map((request) => {
            const isApproved = request.status === 'approved';
            const statusColor = isApproved 
              ? 'bg-green-100 text-green-800 ring-green-200' 
              : 'bg-red-100 text-red-800 ring-red-200';
            
            return (
              <li key={`record-${request.id}`}>
                <div className="px-4 py-3 sm:px-6">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-gray-900">
                            {getEmployeeName(request)} — {request.leave_type_name}
                          </p>
                          <p className="text-xs text-gray-500">
                            {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()} 
                            <span className="ml-1">({request.total_days} working days)</span>
                          </p>
                          {request.reason && (
                            <p className="text-xs text-gray-600 mt-1">
                              <strong>Reason:</strong> {request.reason}
                            </p>
                          )}
                          {request.approval_comments && (
                            <p className="text-xs text-gray-600 mt-1">
                              <strong>Comments:</strong> {request.approval_comments}
                            </p>
                          )}
                          <div className="text-xs text-gray-400 mt-1">
                            Submitted: {new Date(request.created_at).toLocaleDateString()} | 
                            {request.approved_by_name && (
                              <span> Processed by: {request.approved_by_name}</span>
                            )}
                          </div>
                        </div>
                        <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${statusColor}`}>
                          {isApproved ? 'Approved' : 'Rejected'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </li>
            );
          })
        ) : (
          <li><div className="px-4 py-12 text-center">
            {!hasSearched ? (
              <div className="space-y-2">
                <p className="text-sm text-gray-500">Use the search above to find leave records</p>
                <p className="text-xs text-gray-400">Search by employee name, leave type, or filter by status</p>
              </div>
            ) : (
              <p className="text-sm text-gray-500">No records found matching your search criteria.</p>
            )}
          </div></li>
        )}
      </ul>
      {hasSearched && (
        <div className="px-4 py-3 flex items-center justify-between">
          <button
            onClick={() => fetchLeaveRecords(Math.max(recordsPage - 1, 0), recordsSearch, statusFilter)}
            disabled={recordsPage === 0}
            className="px-3 py-1 rounded border text-sm disabled:opacity-50 hover:bg-gray-50"
          >
            Previous
          </button>
          <div className="text-xs text-gray-500">
            Page {recordsPage + 1} 
            {statusFilter && <span className="ml-1">({statusFilter})</span>}
          </div>
          <button
            onClick={() => fetchLeaveRecords(recordsPage + 1, recordsSearch, statusFilter)}
            disabled={!recordsHasMore}
            className="px-3 py-1 rounded border text-sm disabled:opacity-50 hover:bg-gray-50"
          >
            Next
          </button>
        </div>
      )}
      {/* Reject Reason Modal */}
      <Dialog open={rejectModal.open} onClose={() => setRejectModal({ open: false, requestId: null, reason: '' })} className="relative z-50">
        <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="mx-auto w-full max-w-md rounded bg-white p-6 shadow-lg">
            <Dialog.Title className="text-lg font-semibold text-gray-900">Reject Request</Dialog.Title>
            <Dialog.Description className="mt-1 text-sm text-gray-600">
              Please provide a reason for rejection. This reason will be visible to the employee.
            </Dialog.Description>
            <div className="mt-4">
              <label htmlFor="reject-reason" className="block text-sm font-medium text-gray-700">Reason</label>
              <textarea
                id="reject-reason"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                rows={4}
                value={rejectModal.reason}
                onChange={(e) => setRejectModal((prev) => ({ ...prev, reason: e.target.value }))}
                required
                aria-required="true"
              />
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button
                onClick={() => setRejectModal({ open: false, requestId: null, reason: '' })}
                className="px-4 py-2 rounded-md border text-sm text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (!rejectModal.reason.trim()) {
                    showToast({ type: 'error', message: 'Rejection reason is required.' });
                    return;
                  }
                  handleAction(rejectModal.requestId, 'reject', rejectModal.reason.trim());
                  setRejectModal({ open: false, requestId: null, reason: '' });
                }}
                className="px-4 py-2 rounded-md text-sm text-white bg-red-600 hover:bg-red-700"
              >
                Reject Request
              </button>
            </div>
          </Dialog.Panel>
        </div>
      </Dialog>
    </div>
  );
}

export default ManagerDashboard;