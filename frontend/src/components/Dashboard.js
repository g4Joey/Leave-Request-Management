import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';

function Dashboard() {
  const { user } = useAuth();
  const [balances, setBalances] = useState([]);
  const [recentRequests, setRecentRequests] = useState([]);
  const [recentApprovals, setRecentApprovals] = useState([]);
  const [loading, setLoading] = useState(true);

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
            api.get('/leaves/requests/?limit=5')
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
      'rejected': 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
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
                        <p className="text-2xl font-bold text-primary-600">
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
            </h3>
          {recentRequests.length > 0 ? (
            <div className="flow-root">
              <ul className="-my-5 divide-y divide-gray-200">
                {recentRequests.map((request) => (
                  <li key={request.id} className="py-4">
                    <div className="flex items-center space-x-4">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {isMerbanCEO && request.employee_name 
                            ? `${request.employee_name} - ${request.leave_type_name || 'Leave Request'}`
                            : request.leave_type_name || 'Leave Request'
                          }
                        </p>
                        <p className="text-sm text-gray-500">
                          {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()} • {request.total_days} day{request.total_days === 1 ? '' : 's'}
                        </p>
                        {/* Final approver timestamp for requesters: Merban -> CEO, SDSL/SBL -> HR. Show approved or rejected with time */}
                        {(() => {
                          const affiliateName = user?.affiliate_name || '';
                          const isMerban = String(affiliateName).toUpperCase() === 'MERBAN CAPITAL';
                          const isSdslOrSbl = ['SDSL', 'SBL'].includes(String(affiliateName).toUpperCase());
                          const ceoDate = request.ceo_approval_date || null;
                          const hrDate = request.hr_approval_date || null;
                          const finalDate = request.approval_date || null;

                          if (isMerban && ceoDate) {
                            const label = (request.status === 'rejected') ? 'CEO rejected' : 'CEO approved';
                            return (<p className="text-xs text-blue-600 mt-1">{label}: {formatDateTime(ceoDate)}</p>);
                          }

                          if (isSdslOrSbl && hrDate) {
                            const label = (request.status === 'rejected') ? 'HR rejected' : 'HR approved';
                            return (<p className="text-xs text-blue-600 mt-1">{label}: {formatDateTime(hrDate)}</p>);
                          }

                          // Fallback: if there's a final approval/rejection date, show it generically
                          if (finalDate) {
                            const label = (request.status === 'rejected') ? 'Final rejection' : 'Final approval';
                            return (<p className="text-xs text-blue-600 mt-1">{label}: {formatDateTime(finalDate)}</p>);
                          }
                          return null;
                        })()}
                        {isMerbanCEO && request.employee_department && (
                          <p className="text-xs text-gray-400 mt-1">
                            Department: {request.employee_department}
                          </p>
                        )}
                        {isMerbanCEO && request.ceo_approval_date && (
                          <p className="text-xs text-blue-600 mt-1">
                            Processed on: {new Date(request.ceo_approval_date).toLocaleDateString()}
                          </p>
                        )}
                        {request.reason && !isMerbanCEO && (
                          <p className="text-xs text-gray-400 mt-1">
                            {request.reason}
                          </p>
                        )}
                      </div>
                      <div className="flex-shrink-0">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(request.status)}`}>
                          {(request.stage_label && ['pending','manager_approved','hr_approved','ceo_approved'].includes(request.status))
                            ? request.stage_label
                            : request.status_display || request.status}
                        </span>
                      </div>
                    </div>
                  </li>
                ))}
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
                              return lines.map((ln, i) => (
                                <p key={i} className="text-xs text-blue-600">{ln.label}: {ln.date.toLocaleDateString()} {ln.date.toLocaleTimeString()}</p>
                              ));
                            })()}
                          </div>
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