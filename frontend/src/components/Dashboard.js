import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import api from '../services/api';

function Dashboard() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [balances, setBalances] = useState([]);
  const [recentRequests, setRecentRequests] = useState([]);
  const [recentApprovals, setRecentApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [recallLoadingId, setRecallLoadingId] = useState(null);
  const [expandedIds, setExpandedIds] = useState(new Set());

  // Determine if user is Merban Capital CEO (the only CEO who doesn't request leave)
  const isMerbanCEO = user?.role === 'ceo' && user?.affiliate_name === 'Merban Capital';
  
  // Determine if user is an approver who should see split view (managers, HR, SDSL/SBL CEOs)
  const isApprover = user?.role === 'manager' || user?.role === 'hr' || 
    (user?.role === 'ceo' && (user?.affiliate_name === 'SDSL' || user?.affiliate_name === 'SBL'));

  useEffect(() => {
    const fetchData = async () => {
      try {
        console.log('Fetching dashboard data...');
        console.log('Current user:', user);
        console.log('Token in localStorage:', localStorage.getItem('token') ? 'EXISTS' : 'NOT_FOUND');
        console.log('API base URL:', api.defaults.baseURL);
        
        // Only Merban Capital CEO gets the special CEO dashboard
        if (isMerbanCEO) {
          // Use dedicated endpoint that returns items the CEO acted on
          const actedRequestsRes = await api.get('/leaves/manager/recent_activity/?limit=15');
          const acted = actedRequestsRes.data.results || actedRequestsRes.data || [];
          setRecentRequests(Array.isArray(acted) ? acted.slice(0, 5) : []);
          setBalances([]); // Merban CEO doesn't have leave balances
        } else {
          // For approvers (managers, HR, SDSL/SBL CEOs), fetch both own requests and recent approvals
          // For regular staff, just fetch own requests
          const fetchPromises = [
            api.get('/leaves/balances/current_year_full/'),
            api.get('/leaves/requests/recent_combined/?limit=6')
          ];
          
          if (isApprover) {
            fetchPromises.push(api.get('/leaves/manager/recent_activity/?limit=5'));
          }
          
          const responses = await Promise.all(fetchPromises);
          const [balancesRes, requestsRes, approvalsRes] = responses;
          
          console.log('Balances response status:', balancesRes.status);
          console.log('Balances response headers:', balancesRes.headers);
          console.log('Balances response data:', balancesRes.data);
          console.log('Requests response status:', requestsRes.status);
          console.log('Requests response data:', requestsRes.data);
          
          const balancesData = balancesRes.data.results || balancesRes.data;
          const requestsData = requestsRes.data.results || requestsRes.data;
          
                  console.log('Processed balances data:', balancesData);
                  console.log('Balances data type:', typeof balancesData);
                  console.log('Balances data is array:', Array.isArray(balancesData));
                  console.log('Balances data length:', balancesData?.length);
                  
                  // Debug first balance item structure
                  if (balancesData && balancesData.length > 0) {
                    console.log('First balance item:', balancesData[0]);
                    console.log('First balance leave_type:', balancesData[0].leave_type);
                    console.log('First balance leave_type.name:', balancesData[0].leave_type?.name);
                  }          console.log('Processed requests data:', requestsData);
          console.log('Requests data type:', typeof requestsData);
          console.log('Requests data is array:', Array.isArray(requestsData));
          console.log('Requests data length:', requestsData?.length);
          
          setBalances(balancesData);
          setRecentRequests(requestsData);
          
          // Set recent approvals for approvers
          if (isApprover && approvalsRes) {
            const approvalsData = approvalsRes.data.results || approvalsRes.data;
            setRecentApprovals(approvalsData);
          }
        }
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
        console.error('Error status:', error.response?.status);
        console.error('Error data:', error.response?.data);
        console.error('Error message:', error.message);
        console.error('Full error object:', error);
        
        // Set empty arrays to show "No data" messages instead of loading forever
        setBalances([]);
        setRecentRequests([]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    const handleRecallAction = async (request, action) => {
      if (!request?.id) return;
      const endpoint = action === 'accept' ? 'accept_recall' : 'reject_recall';
      setRecallLoadingId(`${request.id}-${action}`);
      try {
        const res = await api.post(`/leaves/requests/${request.id}/${endpoint}/`, { reason: '' });
        const credited = res?.data?.credited_days;
        const suffix = credited ? ` (${credited} days credited)` : '';
        showToast({ type: 'success', message: `Recall ${action === 'accept' ? 'accepted' : 'rejected'}${suffix}` });
        // Refresh recent requests so buttons disappear
        const refreshed = await api.get('/leaves/requests/recent_combined/?limit=6');
        const data = refreshed.data.results || refreshed.data || [];
        setRecentRequests(data);
      } catch (error) {
        console.error('Recall action failed', error);
        const msg = error?.response?.data?.detail || error?.response?.data?.error || 'Failed to respond to recall.';
        showToast({ type: 'error', message: msg });
      } finally {
        setRecallLoadingId(null);
      }
    };
  }, [user]);

  const formatDateTime = (d) => {
    if (!d) return '';
    try {
      const dt = new Date(d);
      if (isNaN(dt)) return String(d);
      return `${dt.toLocaleDateString()} ${dt.toLocaleTimeString()}`;
    } catch (e) {
      return String(d);
    }
  };

  const getFinalActor = (request) => {
    const candidates = [
      { role: 'manager', date: request.manager_approval_date },
      { role: 'hr', date: request.hr_approval_date },
      { role: 'ceo', date: request.ceo_approval_date },
      { role: 'final', date: request.approval_date },
    ].filter(c => c.date);

    if (candidates.length === 0) return null;
    // pick latest
    let latest = candidates[0];
    candidates.forEach(c => {
      try {
        const a = new Date(c.date);
        const b = new Date(latest.date);
        if (a > b) latest = c;
      } catch (e) {}
    });
    // map role to label
    const labelMap = { manager: 'Manager', hr: 'HR', ceo: 'CEO', final: 'Final' };
    return { role: latest.role, label: labelMap[latest.role] || latest.role, date: latest.date };
  };

  const getStatusColor = (status) => {
    const colors = {
      'pending': 'bg-yellow-100 text-yellow-800',
      'approved': 'bg-green-100 text-green-800',
      'rejected': 'bg-red-100 text-red-800',
      'pending_manager': 'bg-yellow-100 text-yellow-800',
      'pending_hr': 'bg-yellow-100 text-yellow-800',
      'pending_staff': 'bg-yellow-100 text-yellow-800',
      'applied': 'bg-green-100 text-green-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const formatActionLabel = (ev) => {
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

  const renderSummaryLine = (request) => {
    if (request.final_event) {
      const ts = request.final_event.timestamp || request.final_event.date;
      const label = request.final_event.label || 'Final decision';
      return (
        <p className="text-xs text-gray-600 mt-1">
          {label} — {ts ? formatDateTime(ts) : ''}
        </p>
      );
    }
    const ev = (request.timeline_events || []).slice().reverse().find((e) => {
      const act = e.action || '';
      return act.includes('approved') || act.includes('rejected') || act === 'finalized';
    });
    if (!ev) return null;
    const label = formatActionLabel(ev);
    return (
      <p className="text-xs text-gray-600 mt-1">
        {label} — {formatDateTime(ev.timestamp)}
      </p>
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
      <div className="bg-white overflow-hidden shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
            {user?.first_name ? `Welcome ${user.first_name}` : 'Welcome to  Merban Leave'}
          </h3>
          <p className="text-sm text-gray-600">
            {isMerbanCEO
              ? 'View your recently processed leave requests and approval decisions.'
              : 'Track your leave balances, submit new requests, and view your leave history.'
            }
          </p>
        </div>
      </div>

      {/* Leave Balances - Not shown for Merban CEO only */}
      {!isMerbanCEO && (
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              Leave Balances
            </h3>
            {balances.length > 0 ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {balances.map((balance, index) => (
                  <div key={index} className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">
                          {balance.leave_type?.name || balance.leave_type_name || 'Leave Type'}
                        </p>
                        <p className="text-2xl font-bold" style={{ color: 'var(--primary)' }}>
                          {balance.remaining_days || 0}
                        </p>
                        <p className="text-xs text-gray-500">
                          of {balance.entitled_days || 0} days remaining
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div>
                <p className="text-gray-500">No leave balances found.</p>
                <p className="text-xs text-gray-400 mt-2">Debug: balances.length = {balances.length}</p>
                <p className="text-xs text-gray-400">User: {user?.email || 'Not logged in'}</p>
                <p className="text-xs text-gray-400">Token: {localStorage.getItem('token') ? 'EXISTS' : 'MISSING'}</p>
                {process.env.NODE_ENV === 'development' && (
                  <pre className="text-xs text-gray-400 mt-2 bg-gray-100 p-2 rounded">
                    {JSON.stringify(balances, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Recent Leave Requests and Approvals - Split view for approvers, full width for others */}
      <div className={isApprover ? 'grid grid-cols-1 lg:grid-cols-2 gap-6' : ''}>
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              {isMerbanCEO ? 'Recently Processed Requests' : 'Recent Leave Requests'}
              {!isMerbanCEO && (() => {
                const recallCount = recentRequests.filter(r => r.has_pending_recall).length;
                return recallCount > 0 ? (
                  <span className="ml-2 inline-flex items-center px-2 py-0.5 text-xs font-semibold rounded-full bg-amber-100 text-amber-800">
                    {recallCount} recall pending
                  </span>
                ) : null;
              })()}
            </h3>
          {recentRequests.length > 0 ? (
            <div className="flow-root">
              <ul className="-my-3 divide-y divide-gray-200">
                {recentRequests.map((request) => {
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

                  const finalBanner = (() => {
                    const finalEv = request.final_event;
                    if (!finalEv) return null;
                    const ts = finalEv.timestamp || finalEv.date;
                    return (
                      <div className="text-xs text-green-700 bg-green-50 border border-green-200 rounded-md px-2 py-1 inline-flex items-center gap-2 select-text">
                        <span className="font-semibold">{finalEv.label || 'Final decision'}</span>
                        <span className="text-gray-600">{ts ? formatDateTime(ts) : ''}</span>
                      </div>
                    );
                  })();

                  const interruptionChip = (() => {
                    if (!request.interruption) return null;
                    return (
                      <div className="text-xs text-blue-800 bg-blue-50 border border-blue-200 rounded-md px-2 py-1 select-text">
                        Interruption: {request.interruption.note}
                        {request.interruption.timestamp ? ` — ${formatDateTime(request.interruption.timestamp)}` : ''}
                      </div>
                    );
                  })();

                  return (
                    <li key={key} className="py-3 select-text">
                      <div className="w-full text-left">
                        <div className="flex items-start justify-between" onClick={toggleExpanded}>
                          <div>
                            <p className="text-sm font-semibold text-gray-900">{isInterrupt ? (request.type_label || 'Interruption') : (request.leave_type_name || 'Leave Request')}</p>
                            <p className="text-xs text-gray-500">
                              {request.start_date ? `${new Date(request.start_date).toLocaleDateString()} - ${new Date(request.end_date).toLocaleDateString()}` : 'No date'}
                              {request.total_days ? ` • ${request.total_days} day${request.total_days === 1 ? '' : 's'}` : ''}
                            </p>
                            {isInterrupt && request.requested_resume_date && (
                              <p className="text-xs text-gray-600">Requested resume: {new Date(request.requested_resume_date).toLocaleDateString()}</p>
                            )}
                          </div>
                          <div className="flex flex-col items-end gap-2">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(request.status)}`}>
                              {(request.stage_label && ['pending','manager_approved','hr_approved','ceo_approved'].includes(request.status))
                                ? request.stage_label
                                : (request.status_display || request.status)
                              }
                            </span>
                            {finalBanner}
                            {interruptionChip}
                          </div>
                        </div>
                        {!isInterrupt && request.has_pending_recall && (
                          <div className="mt-2 flex gap-2">
                            <button
                              onClick={(e) => { e.stopPropagation(); handleRecallAction(request, 'accept'); }}
                              disabled={recallLoadingId === `${request.id}-accept`}
                              className="inline-flex items-center px-3 py-1.5 border border-green-300 text-xs font-medium rounded-md text-green-700 bg-white hover:bg-green-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                            >
                              {recallLoadingId === `${request.id}-accept` ? 'Accepting...' : 'Accept Recall'}
                            </button>
                            <button
                              onClick={(e) => { e.stopPropagation(); handleRecallAction(request, 'reject'); }}
                              disabled={recallLoadingId === `${request.id}-reject`}
                              className="inline-flex items-center px-3 py-1.5 border border-red-300 text-xs font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                            >
                              {recallLoadingId === `${request.id}-reject` ? 'Rejecting...' : 'Reject Recall'}
                            </button>
                          </div>
                        )}
                        {expanded && (
                          <div className="mt-3 space-y-2 text-sm text-gray-700">
                            {!isInterrupt && request.reason && <div className="select-text">Reason: {request.reason}</div>}
                            {isInterrupt && request.reason && <div className="select-text">{request.type_label || 'Interruption'} reason: {request.reason}</div>}
                            {request.timeline_events && request.timeline_events.length > 0 && !isInterrupt && (
                              <div className="space-y-2">
                                {(() => {
                                  const findEvent = (predicate) => (request.timeline_events || []).find(predicate);
                                  const submitted = findEvent((e) => e.action === 'submitted');
                                  const mgr = findEvent((e) => e.action === 'manager_approved');
                                  const hr = findEvent((e) => e.action === 'hr_approved');
                                  const ceo = findEvent((e) => e.action === 'ceo_approved' || e.action === 'finalized');
                                  const interruptions = (request.timeline_events || []).filter((e) => (e.action || '').includes('recall') || (e.action || '').includes('early_return'));
                                  const fmt = (e, label) => e ? <div className="text-xs text-gray-700 select-text" key={label}><span className="font-semibold">{label}:</span> {formatDateTime(e.timestamp)}</div> : null;
                                  return (
                                    <>
                                      {fmt(submitted, 'Requested')}
                                      {fmt(mgr, 'Manager decision')}
                                      {fmt(hr, 'HR decision')}
                                      {fmt(ceo, 'CEO decision')}
                                      {interruptions.length > 0 && (
                                        <div className="text-xs text-gray-700 select-text">
                                          <div className="font-semibold">Interruptions</div>
                                          <div className="space-y-1 mt-1">
                                            {interruptions.map((ev, idx) => (
                                              <div key={idx}>
                                                {formatActionLabel(ev)} — {formatDateTime(ev.timestamp)}{ev.note ? ` (${ev.note})` : ''}
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      )}
                                    </>
                                  );
                                })()}
                              </div>
                            )}
                            {isInterrupt && request.pending_with && (
                              <div className="text-xs text-gray-600 select-text">Pending with: {request.pending_with}</div>
                            )}
                          </div>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : (
            <div>
              <p className="text-gray-500">
                {isMerbanCEO
                  ? 'No recently processed requests to display.' 
                  : 'No recent leave requests.'
                }
              </p>
              <p className="text-xs text-gray-400 mt-2">Debug: recentRequests.length = {recentRequests.length}</p>
              <p className="text-xs text-gray-400">User: {user?.email || 'Not logged in'}</p>
              <p className="text-xs text-gray-400">Token: {localStorage.getItem('token') ? 'EXISTS' : 'MISSING'}</p>
              {process.env.NODE_ENV === 'development' && (
                <pre className="text-xs text-gray-400 mt-2 bg-gray-100 p-2 rounded">
                  {JSON.stringify(recentRequests, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Recent Approvals - Only shown for approvers (managers, HR, SDSL/SBL CEOs) */}
      {isApprover && (
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              Recent Approvals
            </h3>
            {recentApprovals.length > 0 ? (
              <div className="flow-root">
                <ul className="-my-5 divide-y divide-gray-200">
                  {recentApprovals.map((request) => (
                    <li key={request.id} className="py-4">
                      <div className="flex items-center space-x-4">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {request.employee_name || 'Employee'} - {request.leave_type_name || 'Leave Request'}
                          </p>
                          <p className="text-sm text-gray-500">
                            {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()} • {request.total_days} day{request.total_days === 1 ? '' : 's'}
                          </p>
                          {request.employee_department && (
                            <p className="text-xs text-gray-400 mt-1">
                              Department: {request.employee_department}
                            </p>
                          )}
                          {/* Approval timeline: show user's own approval as 'You approved', plus subsequent approver approvals */}
                          <div className="mt-1 space-y-1">
                            {(() => {
                              // Helper: normalize affiliate name from request if present
                              const getEmployeeAffiliate = (req) => {
                                const aff = (req.employee_department_affiliate || req.employee_affiliate || '').toString().trim();
                                if (/^merban(\s+capital)?$/i.test(aff)) return 'Merban Capital';
                                if (/^SDSL$/i.test(aff)) return 'SDSL';
                                if (/^SBL$/i.test(aff)) return 'SBL';
                                return aff || 'Other';
                              };

                              const mgrDate = request.manager_approval_date ? new Date(request.manager_approval_date) : null;
                              const hrDate = request.hr_approval_date ? new Date(request.hr_approval_date) : null;
                              const ceoDate = request.ceo_approval_date ? new Date(request.ceo_approval_date) : null;
                              const rejDate = request.rejection_date ? new Date(request.rejection_date) : null;

                              // Build events and pick the latest event (approval or rejection)
                              const events = [];
                              if (mgrDate) events.push({ key: 'manager', date: mgrDate, role: 'Manager', verb: 'approved' });
                              if (hrDate) events.push({ key: 'hr', date: hrDate, role: 'HR', verb: 'approved' });
                              if (ceoDate) events.push({ key: 'ceo', date: ceoDate, role: 'CEO', verb: 'approved' });
                              if (rejDate) events.push({ key: 'rejected', date: rejDate, role: 'Rejected', verb: 'rejected' });

                              if (events.length === 0) return null;

                              events.sort((a, b) => a.date - b.date); // chronological
                              const latest = events[events.length - 1];

                              const lines = [];

                              // Show earlier approvals as context (manager -> HR -> CEO) but don't let them override the final state
                              events.forEach((ev) => {
                                if (ev === latest) return; // skip final for now
                                // show earlier contextual approvals
                                lines.push({ label: `${ev.role} ${ev.verb}`, date: ev.date });
                              });

                              // Build final label respecting the request's final status and current user
                              const affiliate = getEmployeeAffiliate(request);
                              const isMerban = String(affiliate).toUpperCase() === 'MERBAN CAPITAL';
                              const isSdslOrSbl = ['SDSL', 'SBL'].includes(String(affiliate).toUpperCase());

                              let finalLabel = '';
                              let finalIsYou = false;

                              if (latest.key === 'rejected') {
                                // Final rejection — infer likely rejector role by affiliate
                                const rejectorRole = isMerban ? 'CEO' : (isSdslOrSbl ? 'HR' : 'HR');
                                finalIsYou = (user?.role === 'hr' && rejectorRole === 'HR') || (user?.role === 'ceo' && rejectorRole === 'CEO');
                                finalLabel = finalIsYou ? 'You rejected' : `${rejectorRole} rejected`;
                              } else {
                                // Final approval by manager/hr/ceo
                                const roleMap = { manager: 'Manager', hr: 'HR', ceo: 'CEO' };
                                const roleLabel = roleMap[latest.key] || latest.role || 'Approver';
                                finalIsYou = (user?.role === latest.key) || (user?.role === 'ceo' && latest.key === 'ceo');
                                finalLabel = finalIsYou ? 'You approved' : `${roleLabel} approved`;
                              }

                              // Push final line
                              lines.push({ label: finalLabel, date: latest.date });

                              // Render lines (earliest first, final last)
                              return lines.map((ln, i) => {
                                const isFinal = i === lines.length - 1;
                                const cls = isFinal ? (request.status === 'rejected' ? 'text-red-600' : 'text-green-600') : 'text-gray-600';
                                return (<p key={i} className={`text-xs ${cls}`}>{ln.label}: {ln.date.toLocaleDateString()} {ln.date.toLocaleTimeString()}</p>);
                              });
                            })()}
                          </div>
                          {request.interruption_note && (
                            <p className="text-xs text-blue-700 mt-1">
                              {request.interruption_note}
                            </p>
                          )}
                          {request.actual_resume_date && (
                            <p className="text-xs text-gray-600 mt-1">Actual resume: {new Date(request.actual_resume_date).toLocaleDateString()}</p>
                          )}
                        </div>
                        <div className="flex-shrink-0">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(request.status)}`}>
                            {request.status_display || request.status}
                          </span>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-gray-500">No recent approvals to display.</p>
            )}
          </div>
        </div>
      )}
      </div>
    </div>
  );
}

export default Dashboard;