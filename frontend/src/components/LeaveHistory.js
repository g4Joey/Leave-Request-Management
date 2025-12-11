import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import api from '../services/api';
import { emitApprovalChanged } from '../utils/approvalEvents';

function LeaveHistory() {
  const [requests, setRequests] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [cancelModal, setCancelModal] = useState({ open: false, request: null, comments: '', loading: false });
  const [returnModal, setReturnModal] = useState({ open: false, request: null, resumeDate: '', reason: '', loading: false });
  const [resumeModal, setResumeModal] = useState({ open: false, request: null, resumeDate: '', loading: false });
  const [recallModal, setRecallModal] = useState({ open: false, request: null, action: 'accept', reason: '', loading: false });
  const [expandedIds, setExpandedIds] = useState(new Set());
  const { user } = useAuth();
  const { showToast } = useToast();

  const renderTimeline = (events = []) => {
    if (!events || events.length === 0) return null;

    const labelFor = (ev) => {
      const actor = ev.is_self ? 'You' : (ev.actor_name || 'Someone');
      const action = ev.action || '';
      if (action === 'recall_staff_accepted') return `${actor} accepted Manager Recall`;
      if (action === 'recall_requested') return `${actor} Requested Recall`;
      if (action === 'recall_staff_rejected') return `${actor} rejected Manager Recall`;
      if (action === 'early_return_manager_approved') return `${actor} approved Early Return`;
      if (action === 'early_return_manager_rejected') return `${actor} rejected Early Return`;
      if (action === 'early_return_hr_approved') return `${actor} approved Early Return`;
      if (action === 'early_return_hr_rejected') return `${actor} rejected Early Return`;
      return `${actor} ${action.replace(/_/g, ' ')}`;
    };

    return (
      <div className="mt-3 space-y-1 text-xs text-gray-700">
        {events.map((ev, idx) => (
          <div key={idx} className="flex items-start gap-2">
            <span className="text-gray-500">•</span>
            <div>
              <div className="font-semibold">{labelFor(ev)}</div>
              <div className="text-gray-500">{new Date(ev.timestamp).toLocaleString()}</div>
              {ev.note ? <div className="text-gray-600">{ev.note}</div> : null}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const refreshHistory = useCallback(async () => {
    try {
      const response = await api.get('/leaves/requests/history_combined/');
      setRequests(response.data.results || response.data);
    } catch (error) {
      console.error('Error fetching leave history:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshHistory();
  }, [refreshHistory]);

  const filteredRequests = useMemo(() => {
    const q = (searchQuery || '').trim().toLowerCase();
    if (!q) return requests;

    const toISO = (val) => {
      if (!val) return '';
      return String(val).split('T')[0];
    };

    return requests.filter((r) => {
      const isInterrupt = r.record_type === 'interrupt';
      const type = String(
        r.leave_type_name ||
        r.leave_type?.name ||
        (isInterrupt ? r.type_label : '') ||
        ''
      ).toLowerCase();
      const reason = String(r.reason || '').toLowerCase();
      const status = String(r.status_display || r.status || '').toLowerCase();
      const approvers = `${r.manager?.name || ''} ${r.hr?.name || ''} ${r.ceo?.name || ''}`.toLowerCase();
      const dates = `${toISO(r.start_date)} ${toISO(r.end_date)} ${toISO(r.created_at)} ${toISO(r.actual_resume_date)} ${toISO(r.interrupted_at)} ${toISO(r.requested_resume_date)}`.toLowerCase();
      const nums = `${r.working_days || ''} ${r.total_days || ''}`.toLowerCase();
      const pendingWith = String(r.pending_with || '').toLowerCase();

      return (
        type.includes(q) ||
        reason.includes(q) ||
        status.includes(q) ||
        approvers.includes(q) ||
        dates.includes(q) ||
        nums.includes(q) ||
        pendingWith.includes(q)
      );
    });
  }, [requests, searchQuery]);

  const getStatusColor = (status) => {
    const colors = {
      'pending': 'bg-yellow-100 text-yellow-800',
      'manager_approved': 'bg-blue-100 text-blue-800',
      'hr_approved': 'bg-purple-100 text-purple-800',
      'approved': 'bg-green-100 text-green-800',
      'rejected': 'bg-red-100 text-red-800',
      'cancelled': 'bg-gray-100 text-gray-800',
      'pending_manager': 'bg-yellow-100 text-yellow-800',
      'pending_hr': 'bg-yellow-100 text-yellow-800',
      'pending_staff': 'bg-yellow-100 text-yellow-800',
      'applied': 'bg-green-100 text-green-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const canReturnEarly = (request) => {
    if (request.record_type === 'interrupt') return false;
    if (request.status !== 'approved') return false;
    if ((request.interruption_credited_days || 0) > 0) return false;
    const today = new Date();
    const end = new Date(request.end_date);
    return today <= end;
  };

  const getNextWorkingDay = (dateStr) => {
    if (!dateStr) return null;
    const d = new Date(`${dateStr}T00:00:00`);
    if (isNaN(d)) return null;
    const next = new Date(d);
    do {
      next.setDate(next.getDate() + 1);
    } while (next.getUTCDay() === 0 || next.getUTCDay() === 6);
    next.setHours(0, 0, 0, 0);
    return next;
  };

  const canRecordResume = (request) => {
    if (request.record_type === 'interrupt') return false;
    if (request.status !== 'approved') return false;
    if (request.actual_resume_date) return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const unlock = getNextWorkingDay(request.end_date);
    if (!unlock) return false;
    return today >= unlock;
  };

  /**
   * Check if a leave request can be cancelled by the current user.
   * Uses the can_cancel field from the API which is computed server-side.
   * Fallback to client-side check if API field is not available.
   */
  const canCancel = (request) => {
    if (request.record_type === 'interrupt') return false;
    // Prefer the server-computed can_cancel field
    if (request.can_cancel !== undefined) {
      return request.can_cancel === true;
    }

    // Fallback: client-side check (for backward compatibility)
    if (!user) return false;
    if (request.status !== 'pending') return false;

    // Use employee_pk (database ID) if available, fallback to other fields
    const requestEmployeeId = request.employee_pk || request.employee_id || request.employee?.id || request.employee;
    const currentUserId = user.id;

    return String(requestEmployeeId) === String(currentUserId);
  };

  /**
   * Handle the cancellation of a leave request
   */
  const handleCancelRequest = async () => {
    if (!cancelModal.request) return;

    try {
      setCancelModal(prev => ({ ...prev, loading: true }));

      await api.put(`/leaves/manager/${cancelModal.request.id}/cancel/`, {
        comments: cancelModal.comments
      });

      // Refresh the requests list to show updated status
      const response = await api.get('/leaves/requests/history_combined/');
      setRequests(response.data.results || response.data);

      // Close modal and show success message
      setCancelModal({ open: false, request: null, comments: '', loading: false });
      showToast({ type: 'success', message: 'Leave request cancelled successfully' });
    } catch (error) {
      console.error('Error cancelling request:', error);
      setCancelModal(prev => ({ ...prev, loading: false }));

      // Extract error message from response
      const errorMessage = error.response?.data?.error ||
        error.response?.data?.detail ||
        'Failed to cancel request. Please try again.';
      showToast({ type: 'error', message: errorMessage });
    }
  };

  const submitReturnEarly = async () => {
    if (!returnModal.request || !returnModal.resumeDate) {
      showToast({ type: 'error', message: 'Select a resume date to return early.' });
      return;
    }

    try {
      setReturnModal((prev) => ({ ...prev, loading: true }));
      await api.post(`/leaves/requests/${returnModal.request.id}/return_early/`, {
        resume_date: returnModal.resumeDate,
        reason: returnModal.reason
      });
      showToast({ type: 'success', message: 'Early return submitted. Pending manager/HR confirmation.' });
      setReturnModal({ open: false, request: null, resumeDate: '', reason: '', loading: false });
      refreshHistory();
    } catch (error) {
      console.error('Error submitting early return:', error);
      setReturnModal((prev) => ({ ...prev, loading: false }));
      const msg = error.response?.data?.detail || error.response?.data?.error || 'Failed to submit early return.';
      showToast({ type: 'error', message: msg });
    }
  };

  const submitResume = async () => {
    if (!resumeModal.request || !resumeModal.resumeDate) {
      showToast({ type: 'error', message: 'Select your actual resume date.' });
      return;
    }

    try {
      setResumeModal((prev) => ({ ...prev, loading: true }));
      await api.post(`/leaves/requests/${resumeModal.request.id}/resume/`, {
        resume_date: resumeModal.resumeDate
      });
      showToast({ type: 'success', message: 'Resume recorded.' });
      setResumeModal({ open: false, request: null, resumeDate: '', loading: false });
      refreshHistory();
    } catch (error) {
      console.error('Error recording resume:', error);
      setResumeModal((prev) => ({ ...prev, loading: false }));
      const msg = error.response?.data?.detail || error.response?.data?.error || 'Failed to record resume.';
      showToast({ type: 'error', message: msg });
    }
  };

  const submitRecallResponse = async () => {
    if (!recallModal.request) return;
    const endpoint = recallModal.action === 'accept' ? 'accept_recall' : 'reject_recall';
    try {
      setRecallModal((prev) => ({ ...prev, loading: true }));
      const response = await api.post(`/leaves/requests/${recallModal.request.id}/${endpoint}/`, {
        reason: recallModal.reason
      });
      const credited = response?.data?.credited_days;
      const suffix = credited ? ` (${credited} days credited)` : '';
      showToast({ type: 'success', message: `Recall ${endpoint === 'accept_recall' ? 'accepted' : 'rejected'}${suffix}` });
      setRecallModal({ open: false, request: null, action: 'accept', reason: '', loading: false });
      emitApprovalChanged();
      refreshHistory();
    } catch (error) {
      console.error('Error responding to recall:', error);
      setRecallModal((prev) => ({ ...prev, loading: false }));
      const msg = error.response?.data?.detail || error.response?.data?.error || 'Failed to respond to recall.';
      showToast({ type: 'error', message: msg });
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
          {(() => {
            const recallCount = filteredRequests.filter(r => r.has_pending_recall).length;
            return recallCount > 0 ? (
              <span className="ml-2 inline-flex items-center px-2 py-0.5 text-xs font-semibold rounded-full bg-red-600 text-white">
                {recallCount} recall pending
              </span>
            ) : null;
          })()}
        </h3>
        <p className="mt-1 max-w-2xl text-sm text-gray-500">
          All your leave requests, recalls, and early returns.
        </p>
      </div>
      {/* Search for user's leave history */}
      <div className="px-4 sm:px-6 mt-2">
        <input
          type="text"
          placeholder="Search your history (type, reason, approver, date)..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full border rounded-md px-3 py-2 text-sm"
        />
      </div>
      <ul className="divide-y divide-gray-200">
        {filteredRequests.length > 0 ? (
          filteredRequests.map((request) => {
            const key = `${request.record_type || 'leave'}-${request.id}`;
            const isInterrupt = request.record_type === 'interrupt';
            const expanded = expandedIds.has(key);

            const toggleExpanded = () => {
              setExpandedIds(prev => {
                const next = new Set(prev);
                if (next.has(key)) next.delete(key); else next.add(key);
                return next;
              });
            };

            const statusPill = (
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(request.status)}`}>
                {(request.stage_label && ['pending', 'manager_approved', 'hr_approved', 'ceo_approved'].includes(request.status))
                  ? request.stage_label
                  : request.status_display || request.status}
              </span>
            );

            const finalBanner = (() => {
              const finalEv = request.final_event;
              if (!finalEv) return null;
              const ts = finalEv.timestamp || finalEv.date;
              return (
                <div className="text-xs text-green-700 bg-green-50 border border-green-200 rounded-md px-2 py-1 inline-flex items-center gap-2 select-text">
                  <span className="font-semibold">{finalEv.label || 'Final decision'}</span>
                  <span className="text-gray-600">{ts ? new Date(ts).toLocaleString() : ''}</span>
                </div>
              );
            })();

            const interruptionChip = (() => {
              if (!request.interruption) return null;
              return (
                <div className="text-xs text-blue-800 bg-blue-50 border border-blue-200 rounded-md px-2 py-1 select-text">
                  Interruption: {request.interruption.note}
                  {request.interruption.timestamp ? ` — ${new Date(request.interruption.timestamp).toLocaleString()}` : ''}
                </div>
              );
            })();

            return (
              <li key={key} className="select-text">
                <div className="w-full px-4 py-4 sm:px-6">
                  <div className="flex items-start justify-between gap-3">
                    <div
                      className="flex-1 cursor-pointer"
                      onClick={toggleExpanded}
                    >
                      <div className="flex items-center gap-3">
                        {statusPill}
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {isInterrupt ? (request.type_label || 'Interruption') : (request.leave_type_name || 'Leave Request')}
                          </div>
                          <div className="text-sm text-gray-500">
                            {request.start_date ? `${new Date(request.start_date).toLocaleDateString()} - ${new Date(request.end_date).toLocaleDateString()}` : 'No date'}
                            {request.working_days ? ` • ${request.working_days} working day${request.working_days === 1 ? '' : 's'}` : ''}
                          </div>
                          {isInterrupt && request.requested_resume_date && (
                            <div className="text-xs text-gray-600">Requested resume: {new Date(request.requested_resume_date).toLocaleDateString()}</div>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      {finalBanner}
                      {interruptionChip}
                    </div>
                  </div>

                  {expanded && (
                    <div className="mt-3 space-y-3 text-sm text-gray-700">
                      {!isInterrupt && request.reason && (
                        <div className="select-text"><strong>Reason:</strong> {request.reason}</div>
                      )}
                      {isInterrupt && request.reason && (
                        <div className="select-text"><strong>{request.type_label} reason:</strong> {request.reason}</div>
                      )}
                      {request.interruption_note && (
                        <div className="text-blue-800 bg-blue-50 border border-blue-200 rounded-md p-3 select-text">
                          <strong>Interruption:</strong> {request.interruption_note}
                        </div>
                      )}
                      {request.actual_resume_date && (
                        <div className="select-text"><strong>Actual Resume:</strong> {new Date(request.actual_resume_date).toLocaleDateString()}</div>
                      )}
                      {request.manager_comments && (
                        <div className="select-text"><strong>HOD Comments:</strong> {request.manager_comments}</div>
                      )}
                      {!isInterrupt && renderTimeline(request.timeline_events)}
                      {isInterrupt && request.pending_with && (
                        <div className="text-xs text-gray-600 select-text">Pending with: {request.pending_with}</div>
                      )}
                      {isInterrupt && request.leave_request_id && (
                        <div className="text-xs text-gray-600 select-text">Linked leave #{request.leave_request_id}</div>
                      )}

                      {!isInterrupt && (
                        <div className="flex flex-wrap gap-2 pt-2 border-t border-gray-200 mt-2">
                          {canReturnEarly(request) && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                const todayIso = new Date().toISOString().split('T')[0];
                                const maxDate = new Date(request.end_date).toISOString().split('T')[0];
                                const defaultDate = todayIso > maxDate ? maxDate : todayIso;
                                setReturnModal({ open: true, request, resumeDate: defaultDate, reason: '', loading: false });
                              }}
                              className="inline-flex items-center px-3 py-1.5 border border-blue-300 text-sm font-medium rounded-md text-blue-700 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                            >
                              Return Early
                            </button>
                          )}
                          {canRecordResume(request) && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                const todayIso = new Date().toISOString().split('T')[0];
                                const minDate = new Date(request.end_date).toISOString().split('T')[0];
                                const defaultDate = todayIso < minDate ? minDate : todayIso;
                                setResumeModal({ open: true, request, resumeDate: defaultDate, loading: false });
                              }}
                              className="inline-flex items-center px-3 py-1.5 border border-blue-300 text-sm font-medium rounded-md text-blue-700 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                            >
                              Record Resume
                            </button>
                          )}
                          {request.has_pending_recall && (
                            <div className="flex items-center space-x-2">
                              <button
                                onClick={(e) => { e.stopPropagation(); setRecallModal({ open: true, request, action: 'accept', reason: '', loading: false }); }}
                                className="inline-flex items-center px-3 py-1.5 border border-green-300 text-sm font-medium rounded-md text-green-700 bg-white hover:bg-green-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors"
                              >
                                Accept Recall
                              </button>
                              <button
                                onClick={(e) => { e.stopPropagation(); setRecallModal({ open: true, request, action: 'reject', reason: '', loading: false }); }}
                                className="inline-flex items-center px-3 py-1.5 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
                              >
                                Reject Recall
                              </button>
                            </div>
                          )}
                          {canCancel(request) && (
                            <button
                              onClick={(e) => { e.stopPropagation(); setCancelModal({ open: true, request, comments: '', loading: false }); }}
                              className="inline-flex items-center px-3 py-1.5 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
                            >
                              Cancel Request
                            </button>
                          )}
                        </div>
                      )}
                      <div className="text-xs text-gray-400 select-text">Submitted: {request.created_at ? new Date(request.created_at).toLocaleString() : 'N/A'}</div>
                    </div>
                  )}
                </div>
              </li>
            );
          })
        ) : (
          <li>
            <div className="px-4 py-8 text-center text-gray-500">
              No leave requests found.
            </div>
          </li>
        )}
      </ul>

      {/* Cancel Confirmation Modal */}
      {cancelModal.open && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
          <div className="relative mx-auto p-6 border w-full max-w-md shadow-lg rounded-lg bg-white">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Cancel Leave Request
              </h3>
              <button
                onClick={() => setCancelModal({ open: false, request: null, comments: '', loading: false })}
                className="text-gray-400 hover:text-gray-600"
                disabled={cancelModal.loading}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {cancelModal.request && (
              <div className="mb-4 p-3 bg-gray-50 rounded-md">
                <p className="text-sm font-medium text-gray-900">
                  {cancelModal.request.leave_type_name || 'Leave Request'}
                </p>
                <p className="text-sm text-gray-600">
                  {new Date(cancelModal.request.start_date).toLocaleDateString()} - {new Date(cancelModal.request.end_date).toLocaleDateString()}
                </p>
                <p className="text-sm text-gray-500">
                  {cancelModal.request.working_days} working days
                </p>
              </div>
            )}

            <p className="text-sm text-gray-600 mb-4">
              Are you sure you want to cancel this leave request? This action cannot be undone.
            </p>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Reason for cancellation (optional)
              </label>
              <textarea
                value={cancelModal.comments}
                onChange={(e) => setCancelModal(prev => ({ ...prev, comments: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
                rows="3"
                placeholder="Enter your reason for cancelling..."
                disabled={cancelModal.loading}
              />
            </div>

            <div className="flex items-center justify-end space-x-3">
              <button
                onClick={() => setCancelModal({ open: false, request: null, comments: '', loading: false })}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 font-medium transition-colors"
                disabled={cancelModal.loading}
              >
                Keep Request
              </button>
              <button
                onClick={handleCancelRequest}
                disabled={cancelModal.loading}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center"
              >
                {cancelModal.loading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Cancelling...
                  </>
                ) : (
                  'Cancel Request'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Return Early Modal */}
      {returnModal.open && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
          <div className="relative mx-auto p-6 border w-full max-w-md shadow-lg rounded-lg bg-white">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Return Early</h3>
              <button
                onClick={() => setReturnModal({ open: false, request: null, resumeDate: '', reason: '', loading: false })}
                className="text-gray-400 hover:text-gray-600"
                disabled={returnModal.loading}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            {returnModal.request && (
              <div className="mb-3 text-sm text-gray-700">
                {returnModal.request.leave_type_name} • {new Date(returnModal.request.start_date).toLocaleDateString()} - {new Date(returnModal.request.end_date).toLocaleDateString()}
              </div>
            )}
            <label className="block text-sm font-medium text-gray-700 mb-1">Resume Date</label>
            <input
              type="date"
              value={returnModal.resumeDate}
              onChange={(e) => setReturnModal((prev) => ({ ...prev, resumeDate: e.target.value }))}
              min={returnModal.request ? new Date(returnModal.request.start_date).toISOString().split('T')[0] : undefined}
              max={returnModal.request ? new Date(returnModal.request.end_date).toISOString().split('T')[0] : undefined}
              className="w-full border rounded-md px-3 py-2 text-sm mb-3"
              disabled={returnModal.loading}
            />
            <label className="block text-sm font-medium text-gray-700 mb-1">Reason (optional)</label>
            <textarea
              value={returnModal.reason}
              onChange={(e) => setReturnModal((prev) => ({ ...prev, reason: e.target.value }))}
              rows="3"
              className="w-full border rounded-md px-3 py-2 text-sm mb-4"
              disabled={returnModal.loading}
              placeholder="Explain why you're returning early"
            />
            <div className="flex items-center justify-end space-x-3">
              <button
                onClick={() => setReturnModal({ open: false, request: null, resumeDate: '', reason: '', loading: false })}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                disabled={returnModal.loading}
              >
                Cancel
              </button>
              <button
                onClick={submitReturnEarly}
                disabled={returnModal.loading}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {returnModal.loading ? 'Submitting...' : 'Submit Return'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Resume Modal */}
      {resumeModal.open && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
          <div className="relative mx-auto p-6 border w-full max-w-md shadow-lg rounded-lg bg-white">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Record Actual Resume</h3>
              <button
                onClick={() => setResumeModal({ open: false, request: null, resumeDate: '', loading: false })}
                className="text-gray-400 hover:text-gray-600"
                disabled={resumeModal.loading}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            {resumeModal.request && (
              <div className="mb-3 text-sm text-gray-700">
                {resumeModal.request.leave_type_name} • Ends {new Date(resumeModal.request.end_date).toLocaleDateString()}
              </div>
            )}
            <label className="block text-sm font-medium text-gray-700 mb-1">Actual Resume Date</label>
            <input
              type="date"
              value={resumeModal.resumeDate}
              onChange={(e) => setResumeModal((prev) => ({ ...prev, resumeDate: e.target.value }))}
              min={resumeModal.request ? new Date(resumeModal.request.end_date).toISOString().split('T')[0] : undefined}
              className="w-full border rounded-md px-3 py-2 text-sm mb-4"
              disabled={resumeModal.loading}
            />
            <div className="flex items-center justify-end space-x-3">
              <button
                onClick={() => setResumeModal({ open: false, request: null, resumeDate: '', loading: false })}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                disabled={resumeModal.loading}
              >
                Cancel
              </button>
              <button
                onClick={submitResume}
                disabled={resumeModal.loading}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {resumeModal.loading ? 'Saving...' : 'Record Resume'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Recall Response Modal */}
      {recallModal.open && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
          <div className="relative mx-auto p-6 border w-full max-w-md shadow-lg rounded-lg bg-white">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">{recallModal.action === 'accept' ? 'Accept Recall' : 'Reject Recall'}</h3>
              <button
                onClick={() => setRecallModal({ open: false, request: null, action: 'accept', reason: '', loading: false })}
                className="text-gray-400 hover:text-gray-600"
                disabled={recallModal.loading}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            {recallModal.request && (
              <div className="mb-3 text-sm text-gray-700">
                {recallModal.request.leave_type_name} • {new Date(recallModal.request.start_date).toLocaleDateString()} - {new Date(recallModal.request.end_date).toLocaleDateString()}
              </div>
            )}
            <p className="text-sm text-gray-600 mb-3">
              {recallModal.action === 'accept'
                ? 'Confirm you are returning because your manager recalled you. Days will be credited back when applied.'
                : 'Reject the recall request if you cannot return early.'}
            </p>
            <label className="block text-sm font-medium text-gray-700 mb-1">Comments (optional)</label>
            <textarea
              value={recallModal.reason}
              onChange={(e) => setRecallModal((prev) => ({ ...prev, reason: e.target.value }))}
              rows="3"
              className="w-full border rounded-md px-3 py-2 text-sm mb-4"
              disabled={recallModal.loading}
              placeholder="Optional note to your manager"
            />
            <div className="flex items-center justify-end space-x-3">
              <button
                onClick={() => setRecallModal({ open: false, request: null, action: 'accept', reason: '', loading: false })}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                disabled={recallModal.loading}
              >
                Close
              </button>
              <button
                onClick={submitRecallResponse}
                disabled={recallModal.loading}
                className={`px-4 py-2 text-white rounded-md font-medium disabled:opacity-50 disabled:cursor-not-allowed ${recallModal.action === 'accept' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-red-600 hover:bg-red-700'}`}
              >
                {recallModal.loading ? 'Sending...' : recallModal.action === 'accept' ? 'Accept Recall' : 'Reject Recall'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default LeaveHistory;