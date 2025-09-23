import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { Dialog } from '@headlessui/react';
import { useToast } from '../contexts/ToastContext';

function ManagerDashboard() {
  const { showToast } = useToast();
  const [pendingRequests, setPendingRequests] = useState([]);
  const [approvedRequests, setApprovedRequests] = useState([]);
  const [rejectedRequests, setRejectedRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  // Track which action is loading per request id: 'approve' | 'reject' | undefined
  const [loadingActionById, setLoadingActionById] = useState({});
  const [rejectModal, setRejectModal] = useState({ open: false, requestId: null, reason: '' });
  const PAGE_SIZE = 10;
  // Pagination & filters for Approved
  const [approvedPage, setApprovedPage] = useState(0);
  const [approvedHasMore, setApprovedHasMore] = useState(false);
  const [approvedSearch, setApprovedSearch] = useState('');
  // Pagination & filters for Rejected
  const [rejectedPage, setRejectedPage] = useState(0);
  const [rejectedHasMore, setRejectedHasMore] = useState(false);
  const [rejectedSearch, setRejectedSearch] = useState('');
  

  const fetchApproved = useCallback(async (page = approvedPage, search = approvedSearch) => {
    try {
      const res = await api.get('/leaves/manager/', {
        params: { status: 'approved', ordering: '-created_at', limit: PAGE_SIZE, offset: page * PAGE_SIZE, search: search || undefined },
      });
      const data = res.data;
      const items = data.results || data;
      setApprovedRequests(items);
      if (Array.isArray(items)) {
        // If DRF pagination present, prefer next
        if (data && typeof data === 'object' && 'next' in data) {
          setApprovedHasMore(Boolean(data.next));
        } else {
          setApprovedHasMore(items.length === PAGE_SIZE);
        }
      }
      setApprovedPage(page);
    } catch (e) {
      // non-blocking
    }
  }, [PAGE_SIZE, approvedPage, approvedSearch]);

  const fetchRejected = useCallback(async (page = rejectedPage, search = rejectedSearch) => {
    try {
      const res = await api.get('/leaves/manager/', {
        params: { status: 'rejected', ordering: '-created_at', limit: PAGE_SIZE, offset: page * PAGE_SIZE, search: search || undefined },
      });
      const data = res.data;
      const items = data.results || data;
      setRejectedRequests(items);
      if (Array.isArray(items)) {
        if (data && typeof data === 'object' && 'next' in data) {
          setRejectedHasMore(Boolean(data.next));
        } else {
          setRejectedHasMore(items.length === PAGE_SIZE);
        }
      }
      setRejectedPage(page);
    } catch (e) {
      // non-blocking
    }
  }, [PAGE_SIZE, rejectedPage, rejectedSearch]);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [pendingRes] = await Promise.all([
          api.get('/leaves/manager/pending_approvals/'),
        ]);
        setPendingRequests(pendingRes.data.results || pendingRes.data);
        // initial loads for approved/rejected
        await Promise.all([fetchApproved(0, approvedSearch), fetchRejected(0, rejectedSearch)]);
      } catch (error) {
        console.error('Error fetching pending requests:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAll();
  }, [fetchApproved, fetchRejected, approvedSearch, rejectedSearch]);

  const handleAction = async (requestId, action, comments = '') => {
    setLoadingActionById((prev) => ({ ...prev, [requestId]: action }));

    try {
      await api.put(`/leaves/manager/${requestId}/${action}/`, {
        approval_comments: comments || ''
      });
      
      // Remove the request from the list
      setPendingRequests(prev => prev.filter(req => req.id !== requestId));
  // Refresh approved/rejected sections to reflect the change with current filters
  await Promise.all([fetchApproved(approvedPage, approvedSearch), fetchRejected(rejectedPage, rejectedSearch)]);
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

  {/* Approved & Rejected sections */}
      <div className="px-4 py-5 sm:px-6">
        <h4 className="text-md leading-6 font-semibold text-gray-900">Recently Approved</h4>
        <div className="mt-2 flex items-center gap-2">
          <input
            type="text"
            placeholder="Search employee or type"
            value={approvedSearch}
            onChange={(e) => setApprovedSearch(e.target.value)}
            className="w-full max-w-xs rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
          />
          <button
            onClick={() => fetchApproved(0, approvedSearch)}
            className="px-3 py-2 rounded-md bg-gray-100 hover:bg-gray-200 text-sm"
          >
            Apply
          </button>
        </div>
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
      <div className="px-4 py-3 flex items-center justify-between">
        <button
          onClick={() => fetchApproved(Math.max(approvedPage - 1, 0), approvedSearch)}
          disabled={approvedPage === 0}
          className="px-3 py-1 rounded border text-sm disabled:opacity-50"
        >
          Previous
        </button>
        <div className="text-xs text-gray-500">Page {approvedPage + 1}</div>
        <button
          onClick={() => fetchApproved(approvedPage + 1, approvedSearch)}
          disabled={!approvedHasMore}
          className="px-3 py-1 rounded border text-sm disabled:opacity-50"
        >
          Next
        </button>
      </div>

      <div className="px-4 py-5 sm:px-6">
        <h4 className="text-md leading-6 font-semibold text-gray-900">Recently Rejected</h4>
        <div className="mt-2 flex items-center gap-2">
          <input
            type="text"
            placeholder="Search employee or type"
            value={rejectedSearch}
            onChange={(e) => setRejectedSearch(e.target.value)}
            className="w-full max-w-xs rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
          />
          <button
            onClick={() => fetchRejected(0, rejectedSearch)}
            className="px-3 py-2 rounded-md bg-gray-100 hover:bg-gray-200 text-sm"
          >
            Apply
          </button>
        </div>
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
      <div className="px-4 py-3 flex items-center justify-between">
        <button
          onClick={() => fetchRejected(Math.max(rejectedPage - 1, 0), rejectedSearch)}
          disabled={rejectedPage === 0}
          className="px-3 py-1 rounded border text-sm disabled:opacity-50"
        >
          Previous
        </button>
        <div className="text-xs text-gray-500">Page {rejectedPage + 1}</div>
        <button
          onClick={() => fetchRejected(rejectedPage + 1, rejectedSearch)}
          disabled={!rejectedHasMore}
          className="px-3 py-1 rounded border text-sm disabled:opacity-50"
        >
          Next
        </button>
      </div>
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