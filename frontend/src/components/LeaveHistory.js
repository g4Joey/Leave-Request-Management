import React, { useState, useEffect } from 'react';
import api from '../services/api';

function LeaveHistory() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRequests = async () => {
      try {
        const response = await api.get('/leaves/requests/history/');
        setRequests(response.data.results || response.data);
      } catch (error) {
        console.error('Error fetching leave history:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchRequests();
  }, []);

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
    <div className="bg-white shadow overflow-hidden sm:rounded-md">
      <div className="px-4 py-5 sm:px-6">
        <h3 className="text-lg leading-6 font-medium text-gray-900">
          Leave History
        </h3>
        <p className="mt-1 max-w-2xl text-sm text-gray-500">
          All your leave requests and their current status.
        </p>
      </div>
      <ul className="divide-y divide-gray-200">
        {requests.length > 0 ? (
          requests.map((request) => (
            <li key={request.id}>
              <div className="px-4 py-4 sm:px-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(request.status)}`}>
                        {request.status}
                      </span>
                    </div>
                    <div className="ml-4">
                      <div className="text-sm font-medium text-gray-900">
                        {request.leave_type_name || 'Leave Request'}
                      </div>
                      <div className="text-sm text-gray-500">
                        {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  <div className="text-sm text-gray-500">
                    {request.working_days} working days
                  </div>
                </div>
                {request.reason && (
                  <div className="mt-2 text-sm text-gray-600">
                    <strong>Reason:</strong> {request.reason}
                  </div>
                )}
                {request.manager_comments && (
                  <div className="mt-2 text-sm text-gray-600">
                    <strong>Manager Comments:</strong> {request.manager_comments}
                  </div>
                )}
                <div className="mt-2 text-xs text-gray-400">
                  Submitted: {new Date(request.created_at).toLocaleString()}
                </div>
              </div>
            </li>
          ))
        ) : (
          <li>
            <div className="px-4 py-8 text-center text-gray-500">
              No leave requests found.
            </div>
          </li>
        )}
      </ul>
    </div>
  );
}

export default LeaveHistory;