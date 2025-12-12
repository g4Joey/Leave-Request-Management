import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import Skeleton from './common/Skeleton';
import { Clock, Calendar, PieChart, CheckCircle, XCircle, AlertCircle, TrendingUp } from 'lucide-react';

function Dashboard() {
  const { user } = useAuth();
  const [balances, setBalances] = useState([]);
  const [recentRequests, setRecentRequests] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        if (user?.role === 'ceo') {
          const actedRequestsRes = await api.get('/leaves/manager/recent_activity/?limit=15');
          const acted = actedRequestsRes.data.results || actedRequestsRes.data || [];
          setRecentRequests(Array.isArray(acted) ? acted.slice(0, 5) : []);
          setBalances([]);
        } else {
          const [balancesRes, requestsRes] = await Promise.all([
            api.get('/leaves/balances/current_year_full/'),
            api.get('/leaves/requests/?limit=5')
          ]);

          setBalances(balancesRes.data.results || balancesRes.data);
          setRecentRequests(requestsRes.data.results || requestsRes.data);
        }
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
        setBalances([]);
        setRecentRequests([]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user]);

  const getStatusColor = (status) => {
    const statusMap = {
      'pending': 'bg-yellow-100 text-yellow-700 border-yellow-200',
      'approved': 'bg-green-100 text-green-700 border-green-200',
      'rejected': 'bg-red-100 text-red-700 border-red-200'
    };
    return statusMap[status] || 'bg-gray-100 text-gray-700 border-gray-200';
  };

  const getLeaveIcon = (type) => {
    const name = (type?.name || type || '').toLowerCase();
    if (name.includes('sick')) return <AlertCircle className="w-5 h-5" />;
    if (name.includes('vacation') || name.includes('annual')) return <Calendar className="w-5 h-5" />;
    return <Clock className="w-5 h-5" />;
  };

  if (loading) {
    return (
      <div className="space-y-8 animate-fade-in">
        {/* Welcome Banner Skeleton */}
        <div className="glass-panel rounded-2xl p-8 h-40 flex flex-col justify-center gap-4">
           <Skeleton className="h-8 w-1/3" />
           <Skeleton className="h-4 w-1/2" />
        </div>

        {/* Cards Grid Skeleton */}
        {user?.role !== 'ceo' && (
           <div>
              <Skeleton className="h-6 w-40 mb-6" />
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="glass-card p-6 h-40 flex flex-col justify-between">
                     <div className="flex justify-between">
                        <Skeleton className="h-10 w-10 rounded-lg" />
                        <Skeleton className="h-6 w-16" />
                     </div>
                     <div className="space-y-2">
                        <Skeleton className="h-4 w-24" />
                        <Skeleton className="h-8 w-16" />
                     </div>
                  </div>
                ))}
              </div>
           </div>
        )}

        {/* Activity List Skeleton */}
        <div>
           <Skeleton className="h-6 w-48 mb-6" />
           <div className="glass-panel rounded-xl overflow-hidden p-6 space-y-4">
              {[1, 2, 3].map((i) => (
                 <div key={i} className="flex justify-between items-center py-4 border-b border-gray-100 last:border-0">
                    <div className="flex items-center gap-4 w-1/3">
                       <Skeleton className="h-10 w-10 rounded-full" />
                       <div className="space-y-2 flex-1">
                          <Skeleton className="h-4 w-3/4" />
                          <Skeleton className="h-3 w-1/2" />
                       </div>
                    </div>
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-4 w-16" />
                    <Skeleton className="h-6 w-20 rounded-full" />
                 </div>
              ))}
           </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Welcome Section */}
      <div className="glass-panel rounded-2xl p-8 relative overflow-hidden">
        <div className="relative z-10">
          <h1 className="text-3xl font-bold text-primary font-heading mb-2">
            Hello, {user?.first_name || 'Team Member'} 👋
          </h1>
          <p className="text-gray-600 max-w-2xl">
            {user?.role === 'ceo'
              ? 'Here is an overview of your recent approval activities.'
              : 'Here is your leave summary for the year. Plan your time off effectively.'
            }
          </p>
        </div>
        <div className="absolute top-0 right-0 w-64 h-64 bg-accent/10 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none"></div>
      </div>

      {/* Leave Balances Grid - Not for CEO */}
      {user?.role !== 'ceo' && (
        <div>
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-bold text-primary font-heading flex items-center gap-2">
              <PieChart className="w-5 h-5 text-accent" />
              Leave Balances
            </h3>
          </div>

          {balances.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {balances.map((balance, index) => (
                <div key={index} className="glass-card hover:bg-white/80 transition-all duration-300 rounded-xl p-6 relative group overflow-hidden border-l-4 border-l-accent">
                  <div className="flex justify-between items-start mb-4">
                    <div className="p-3 bg-primary/5 rounded-lg group-hover:bg-primary/10 transition-colors">
                      {getLeaveIcon(balance.leave_type)}
                    </div>
                    <span className="text-xs font-semibold text-primary/60 bg-primary/5 px-2 py-1 rounded-md">
                      {Math.round((balance.remaining_days / balance.entitled_days) * 100)}% Left
                    </span>
                  </div>

                  <h4 className="text-gray-600 font-medium text-sm uppercase tracking-wide mb-1">
                    {balance.leave_type?.name || 'Leave Type'}
                  </h4>

                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-extrabold text-primary font-heading">
                      {balance.remaining_days}
                    </span>
                    <span className="text-sm text-gray-500 font-medium">
                      / {balance.entitled_days} days
                    </span>
                  </div>

                  {/* Progress Bar */}
                  <div className="mt-4 w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-accent h-full rounded-full transition-all duration-1000 ease-out"
                      style={{ width: `${(balance.remaining_days / balance.entitled_days) * 100}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="glass-panel p-8 rounded-xl text-center text-gray-500">
              No leave balances available.
            </div>
          )}
        </div>
      )}

      {/* Recent Activity Section */}
      <div>
        <h3 className="text-xl font-bold text-primary font-heading mb-6 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-accent" />
          {user?.role === 'ceo' ? 'Recent Decisions' : 'Recent History'}
        </h3>

        <div className="glass-panel rounded-xl overflow-hidden shadow-sm">
          {recentRequests.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-primary/5 text-gray-700 text-xs font-bold uppercase tracking-wider text-left font-heading">
                  <tr>
                    <th className="px-6 py-4">Request Details</th>
                    <th className="px-6 py-4">Dates</th>
                    {user?.role === 'ceo' && <th className="px-6 py-4">Employee</th>}
                    <th className="px-6 py-4">Duration</th>
                    <th className="px-6 py-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {recentRequests.map((request) => (
                    <tr key={request.id} className="hover:bg-primary/5 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-full bg-white shadow-sm border border-gray-100 text-accent">
                            {getLeaveIcon(request.leave_type_name)}
                          </div>
                          <div>
                            <span className="block font-semibold text-gray-900">
                              {request.leave_type_name || 'Leave Request'}
                            </span>
                            <span className="text-xs text-gray-500 line-clamp-1 max-w-[200px]">
                              {request.reason || 'No reason provided'}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()}
                      </td>
                      {user?.role === 'ceo' && (
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-gray-900">{request.employee_name}</div>
                          <div className="text-xs text-gray-500">{request.employee_department}</div>
                        </td>
                      )}
                      <td className="px-6 py-4">
                        <span className="font-mono font-medium text-gray-700">{request.total_days}</span> <span className="text-xs text-gray-500">days</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${getStatusColor(request.status)}`}>
                          {getStatusIcon(request.status)}
                          <span className="ml-1 capitalize">
                            {(['pending', 'manager_approved', 'hr_approved', 'ceo_approved'].includes(request.status)
                              && (request.status_display || request.stage_label))
                              || request.status_display
                              || request.status}
                          </span>
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-12 text-center">
              <div className="inline-flex p-4 bg-gray-50 rounded-full mb-3 text-gray-400">
                <Clock className="w-8 h-8" />
              </div>
              <p className="text-gray-500 font-medium">No recent activity to show.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const getStatusIcon = (status) => {
  if (status === 'approved') return <CheckCircle className="w-3 h-3" />;
  if (status === 'rejected') return <XCircle className="w-3 h-3" />;
  return <Clock className="w-3 h-3" />;
};

export default Dashboard;