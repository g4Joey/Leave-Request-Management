import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { Dialog } from '@headlessui/react';
import { useToast } from '../contexts/ToastContext';
import OverlapAdvisory from './OverlapAdvisory';
import { emitApprovalChanged } from '../utils/approvalEvents';

function ManagerDashboard() {
  const { showToast } = useToast();
  const [pendingRequests, setPendingRequests] = useState([]);
  const [pendingInterrupts, setPendingInterrupts] = useState([]);
  const [leaveRecords, setLeaveRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  // Track which action is loading per request id: 'approve' | 'reject' | undefined
  const [loadingActionById, setLoadingActionById] = useState({});
  const [rejectModal, setRejectModal] = useState({ open: false, requestId: null, reason: '' });
  const [recallModal, setRecallModal] = useState({ open: false, request: null, resumeDate: '', reason: '', loading: false });
  const PAGE_SIZE = 15;
  // Pagination & filters for Approval Records (approved + rejected)
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
        const [pendingRes, interruptsRes] = await Promise.all([
          api.get('/leaves/manager/pending_approvals/'),
          api.get('/leaves/manager/pending_interrupts/').catch(() => ({ data: { results: [] } })),
        ]);
        // API returns an object { requests: [...], count, user_role, approval_stage }
        const pendingArray = Array.isArray(pendingRes.data)
          ? pendingRes.data
          : (pendingRes.data && Array.isArray(pendingRes.data.requests)
              ? pendingRes.data.requests
              : (pendingRes.data && Array.isArray(pendingRes.data.results)
                  ? pendingRes.data.results
                  : []));
        const interruptArray = Array.isArray(pendingRes.data?.interrupts)
          ? pendingRes.data.interrupts
          : (Array.isArray(interruptsRes?.data?.results) ? interruptsRes.data.results : []);
        setPendingRequests(pendingArray);
        setPendingInterrupts(interruptArray);
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
      emitApprovalChanged();
      // Global toast and optional haptics
      const verb = action === 'approve' ? 'approved' : 'rejected';
      showToast({ type: 'success', message: `Request ${verb} successfully.` });
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

  const openRecallModal = (request) => {
    const todayIso = new Date().toISOString().split('T')[0];
    const maxDate = new Date(request.end_date).toISOString().split('T')[0];
    const minDate = new Date(request.start_date).toISOString().split('T')[0];
    const defaultDate = todayIso > maxDate ? maxDate : todayIso < minDate ? minDate : todayIso;
    setRecallModal({ open: true, request, resumeDate: defaultDate, reason: '', loading: false });
  };

  const handleInterruptAction = async (interruptId, action, reason = '') => {
    const endpoint = action === 'approve' ? 'manager-approve' : 'manager-reject';
    setLoadingActionById((prev) => ({ ...prev, [`interrupt-${interruptId}`]: action }));
    try {
      await api.post(`/leaves/manager/interrupts/${interruptId}/${endpoint}/`, { reason });
      showToast({ type: 'success', message: action === 'approve' ? 'Early return approved (pending HR).' : 'Early return rejected.' });
      setPendingInterrupts((prev) => prev.filter((i) => i.id !== interruptId));
      emitApprovalChanged();
    } catch (error) {
      console.error('Interrupt action failed', error);
      const detail = error?.response?.data?.detail || error?.response?.data?.error || 'Failed to process early return.';
      showToast({ type: 'error', message: detail });
    } finally {
      setLoadingActionById((prev) => ({ ...prev, [`interrupt-${interruptId}`]: undefined }));
    }
  };

  const submitRecall = async () => {
    if (!recallModal.request || !recallModal.resumeDate) {
      showToast({ type: 'error', message: 'Select a resume date for the recall.' });
      return;
    }
    try {
      setRecallModal((prev) => ({ ...prev, loading: true }));
      await api.post(`/leaves/manager/${recallModal.request.id}/recall/`, {
        resume_date: recallModal.resumeDate,
        reason: recallModal.reason
      });
      showToast({ type: 'success', message: 'Recall sent to staff for confirmation.' });
      setRecallModal({ open: false, request: null, resumeDate: '', reason: '', loading: false });
      await fetchLeaveRecords(recordsPage, recordsSearch, statusFilter);
      emitApprovalChanged();
    } catch (error) {
      console.error('Error recalling staff:', error);
      setRecallModal((prev) => ({ ...prev, loading: false }));
      const detail = error?.response?.data?.detail || error?.response?.data?.error || 'Failed to create recall.';
      showToast({ type: 'error', message: detail });
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
          HOD Dashboard
        </h3>
        <p className="mt-1 max-w-2xl text-sm text-gray-500">
          Review and approve pending leave requests.
        </p>
      </div>

      <ul className="divide-y divide-gray-200">
        {pendingRequests.length + pendingInterrupts.length > 0 ? (
          [...pendingInterrupts.map((interrupt) => ({ ...interrupt, _isInterrupt: true })), ...pendingRequests.map((request) => ({ ...request, _isInterrupt: false }))].map((request) => (
            <li key={`${request._isInterrupt ? 'interrupt-' : ''}${request.id}`}>
              <div className={`px-4 py-4 sm:px-6 ${request._isInterrupt ? 'bg-amber-50 border-l-4 border-amber-400' : ''}`}>
                {/* Overlap Advisory Banner */}
                {!request._isInterrupt && (
                  <OverlapAdvisory 
                    leaveRequest={{
                      ...request,
                      employee_department_id: request.employee_department_id || request.department_id,
                      employee_id: request.employee_id || request.employee
                    }}
                    className="mb-3"
                  />
                )}
                
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-primary-600 flex items-center gap-2">
                          {getEmployeeName(request)}
                          {request._isInterrupt && <span className="text-amber-700 text-xs px-2 py-0.5 rounded-full bg-amber-200">Early return</span>}
                        </p>
                        <p className="text-sm text-gray-900">
                          {request.leave_type_name || 'Leave Request'}
                        </p>
                        <p className="text-sm text-gray-500">
                          {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()}
                          <span className="ml-2">({request.total_days} working days)</span>
                        </p>
                        {request._isInterrupt && (
                          <p className="text-xs text-amber-700 mt-1">Requested resume: {new Date(request.requested_resume_date).toLocaleDateString()}</p>
                        )}
                      </div>
                      <div className="flex space-x-2">
                        {request._isInterrupt ? (
                          <>
                            <button
                              onClick={() => handleInterruptAction(request.id, 'approve')}
                              disabled={Boolean(loadingActionById[`interrupt-${request.id}`])}
                              className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
                            >
                              {loadingActionById[`interrupt-${request.id}`] === 'approve' ? 'Processing...' : 'Approve Return'}
                            </button>
                            <button
                              onClick={() => handleInterruptAction(request.id, 'reject')}
                              disabled={Boolean(loadingActionById[`interrupt-${request.id}`])}
                              className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
                            >
                              {loadingActionById[`interrupt-${request.id}`] === 'reject' ? 'Processing...' : 'Reject'}
                            </button>
                          </>
                        ) : (
                          <>
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
                          </>
                        )}
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
                      {request._isInterrupt ? 'Requested' : 'Submitted'}: {new Date(request.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>
              </div>
            </li>
          ))
        ) : (
          <li>
            <div className="px-4 py-8 text-center text-gray-500">
                      <div className="text-center py-12">
                        <svg className="mx-auto h-12 w-12 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <h3 className="text-lg font-medium text-gray-900 mb-2">No pending approvals</h3>
                        <p className="text-gray-500">All staff requests have been processed.</p>
                      </div>
            </div>
          </li>
        )}
      </ul>

      {/* Approval Records Section (Approved & Rejected consolidated) */}
      <div className="px-4 py-5 sm:px-6">
        <h4 className="text-md leading-6 font-semibold text-gray-900">Approval Records</h4>
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
                          {request.interruption_note && (
                            <p className="text-xs text-blue-700 mt-2 bg-blue-50 border border-blue-200 rounded p-2">
                              <strong>Interruption:</strong> {request.interruption_note}
                            </p>
                          )}
                          {request.actual_resume_date && (
                            <p className="text-xs text-gray-600 mt-1">
                              <strong>Actual Resume:</strong> {new Date(request.actual_resume_date).toLocaleDateString()}
                            </p>
                          )}
                          <div className="text-xs text-gray-400 mt-1">
                            Submitted: {new Date(request.created_at).toLocaleDateString()} | 
                            {request.approved_by_name && (
                              <span> Processed by: {request.approved_by_name}</span>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${statusColor}`}>
                            {isApproved ? 'Approved' : 'Rejected'}
                          </span>
                          {isApproved && (request.interruption_credited_days || 0) === 0 && (
                            <button
                              onClick={() => openRecallModal(request)}
                              className="inline-flex items-center px-3 py-1 border border-blue-300 text-xs font-medium rounded-md text-blue-700 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                            >
                              Recall Staff
                            </button>
                          )}
                        </div>
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
                <p className="text-sm text-gray-500">Use the search above to find approval records</p>
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

      {/* Recall Modal */}
      <Dialog open={recallModal.open} onClose={() => setRecallModal({ open: false, request: null, resumeDate: '', reason: '', loading: false })} className="relative z-50">
        <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="mx-auto w-full max-w-md rounded bg-white p-6 shadow-lg">
            <Dialog.Title className="text-lg font-semibold text-gray-900">Recall Staff From Leave</Dialog.Title>
            <Dialog.Description className="mt-1 text-sm text-gray-600">
              Choose the date the staff should resume and optionally add a note.
            </Dialog.Description>
            {recallModal.request && (
              <div className="mt-3 text-sm text-gray-700">
                {recallModal.request.employee_name} — {recallModal.request.leave_type_name}
                <div className="text-xs text-gray-500">{new Date(recallModal.request.start_date).toLocaleDateString()} - {new Date(recallModal.request.end_date).toLocaleDateString()}</div>
              </div>
            )}
            <div className="mt-4 space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Resume Date</label>
                <input
                  type="date"
                  value={recallModal.resumeDate}
                  onChange={(e) => setRecallModal((prev) => ({ ...prev, resumeDate: e.target.value }))}
                  min={recallModal.request ? new Date(recallModal.request.start_date).toISOString().split('T')[0] : undefined}
                  max={recallModal.request ? new Date(recallModal.request.end_date).toISOString().split('T')[0] : undefined}
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
                  disabled={recallModal.loading}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Reason (optional)</label>
                <textarea
                  rows={3}
                  value={recallModal.reason}
                  onChange={(e) => setRecallModal((prev) => ({ ...prev, reason: e.target.value }))}
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
                  disabled={recallModal.loading}
                  placeholder="Add a note for the staff member"
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => setRecallModal({ open: false, request: null, resumeDate: '', reason: '', loading: false })}
                className="px-4 py-2 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50 text-sm"
                disabled={recallModal.loading}
              >
                Cancel
              </button>
              <button
                onClick={submitRecall}
                disabled={recallModal.loading}
                className="px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
              >
                {recallModal.loading ? 'Sending...' : 'Send Recall'}
              </button>
            </div>
          </Dialog.Panel>
        </div>
      </Dialog>
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