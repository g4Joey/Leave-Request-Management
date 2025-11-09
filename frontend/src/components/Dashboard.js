import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';

function Dashboard() {
  const { user } = useAuth();
  const [balances, setBalances] = useState([]);
  const [recentRequests, setRecentRequests] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        console.log('Fetching dashboard data...');
        console.log('Current user:', user);
        console.log('Token in localStorage:', localStorage.getItem('token') ? 'EXISTS' : 'NOT_FOUND');
        console.log('API base URL:', api.defaults.baseURL);
        
        // CEO users get different dashboard data - show recently approved/rejected requests
        if (user?.role === 'ceo') {
          // Use dedicated endpoint that returns items the CEO acted on
          const actedRequestsRes = await api.get('/leaves/manager/recent_activity/?limit=15');
          const acted = actedRequestsRes.data.results || actedRequestsRes.data || [];
          setRecentRequests(Array.isArray(acted) ? acted.slice(0, 5) : []);
          setBalances([]); // CEOs don't have leave balances
        } else {
          const [balancesRes, requestsRes] = await Promise.all([
            api.get('/leaves/balances/current_year_full/'),
            api.get('/leaves/requests/?limit=5')
          ]);
          
          console.log('Balances response status:', balancesRes.status);
          console.log('Balances response headers:', balancesRes.headers);
          console.log('Balances response data:', balancesRes.data);
          console.log('Requests response status:', requestsRes.status);
          console.log('Requests response data:', requestsRes.data);
          
          // Normalize response shapes to arrays regardless of backend pagination/wrappers
          const toArray = (data) => {
            if (Array.isArray(data)) return data;
            if (Array.isArray(data?.results)) return data.results;
            if (Array.isArray(data?.items)) return data.items;
            // Some backends may wrap under a key like 'requests' or 'data'
            if (Array.isArray(data?.requests)) return data.requests;
            if (Array.isArray(data?.data)) return data.data;
            return [];
          };

          const balancesData = toArray(balancesRes.data);
          const requestsData = toArray(requestsRes.data);
          
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
          
          setBalances(Array.isArray(balancesData) ? balancesData : []);
          setRecentRequests(Array.isArray(requestsData) ? requestsData : []);
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
            {user?.role === 'ceo' 
              ? 'View your recently processed leave requests and approval decisions.'
              : 'Track your leave balances, submit new requests, and view your leave history.'
            }
          </p>
        </div>
      </div>

      {/* Leave Balances - Not shown for CEO */}
      {user?.role !== 'ceo' && (
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

      {/* Recent Leave Requests */}
      <div className="bg-white overflow-hidden shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
            {user?.role === 'ceo' ? 'Recently Processed Requests' : 'Recent Leave Requests'}
          </h3>
          {recentRequests.length > 0 ? (
            <div className="flow-root">
              <ul className="-my-5 divide-y divide-gray-200">
                {recentRequests.map((request) => (
                  <li key={request.id} className="py-4">
                    <div className="flex items-center space-x-4">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {user?.role === 'ceo' && request.employee_name 
                            ? `${request.employee_name} - ${request.leave_type_name || 'Leave Request'}`
                            : request.leave_type_name || 'Leave Request'
                          }
                        </p>
                        <p className="text-sm text-gray-500">
                          {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()} • {request.total_days} day{request.total_days === 1 ? '' : 's'}
                        </p>
                        {user?.role === 'ceo' && request.employee_department && (
                          <p className="text-xs text-gray-400 mt-1">
                            Department: {request.employee_department}
                          </p>
                        )}
                        {user?.role === 'ceo' && request.ceo_approval_date && (
                          <p className="text-xs text-blue-600 mt-1">
                            Processed on: {new Date(request.ceo_approval_date).toLocaleDateString()}
                          </p>
                        )}
                        {request.reason && user?.role !== 'ceo' && (
                          <p className="text-xs text-gray-400 mt-1">
                            {request.reason}
                          </p>
                        )}
                      </div>
                      <div className="flex-shrink-0">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(request.status)}`}>
                          {/* Use stage-aware label for pending pipeline statuses when available */}
                          {(['pending','manager_approved','hr_approved','ceo_approved'].includes(request.status) && (request.stage_label || request.status_display)) || request.status}
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
                {user?.role === 'ceo' 
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
    </div>
  );
}

export default Dashboard;