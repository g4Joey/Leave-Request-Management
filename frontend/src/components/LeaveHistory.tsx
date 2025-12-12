import React, { useState, useEffect } from 'react';
import { useToast } from '../contexts/ToastContext';
import api from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Calendar, Clock, AlertCircle, CheckCircle, XCircle, FileText, Ban } from 'lucide-react';
import Skeleton from './common/Skeleton';

function LeaveHistory() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [cancelModal, setCancelModal] = useState({ open: false, request: null, comments: '', loading: false });
  const { showToast } = useToast();

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

  const getStatusConfig = (status) => {
    switch (status) {
      case 'approved': return { color: 'text-green-600 bg-green-100/50 border-green-200', icon: CheckCircle, label: 'Approved' };
      case 'rejected': return { color: 'text-red-600 bg-red-100/50 border-red-200', icon: XCircle, label: 'Rejected' };
      case 'cancelled': return { color: 'text-gray-600 bg-gray-100/50 border-gray-200', icon: Ban, label: 'Cancelled' };
      case 'manager_approved': return { color: 'text-blue-600 bg-blue-100/50 border-blue-200', icon: Clock, label: 'Manager Approved' };
      case 'hr_approved': return { color: 'text-purple-600 bg-purple-100/50 border-purple-200', icon: Clock, label: 'HR Approved' };
      default: return { color: 'text-yellow-600 bg-yellow-100/50 border-yellow-200', icon: Clock, label: 'Pending' };
    }
  };

  const handleCancelRequest = async () => {
    if (!cancelModal.request) return;
    
    try {
      setCancelModal(prev => ({ ...prev, loading: true }));
      await api.put(`/leaves/manager/${cancelModal.request.id}/cancel/`, {
        comments: cancelModal.comments
      });
      
      const response = await api.get('/leaves/requests/history/');
      setRequests(response.data.results || response.data);
      
      setCancelModal({ open: false, request: null, comments: '', loading: false });
      showToast({ type: 'success', message: 'Leave request cancelled successfully' });
    } catch (error) {
      console.error('Error cancelling request:', error);
      setCancelModal(prev => ({ ...prev, loading: false }));
      showToast({ type: 'error', message: error.response?.data?.error || 'Failed to cancel request' });
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-40 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 font-heading">Leave History</h1>
          <p className="text-gray-500 mt-1">Track and manage your leave requests</p>
        </div>
      </div>

      {/* Requests List */}
      <div className="space-y-4">
        <AnimatePresence mode="popLayout">
          {requests.length > 0 ? (
            requests.map((request, index) => {
              const statusConfig = getStatusConfig(request.status);
              const StatusIcon = statusConfig.icon;

              return (
                <motion.div
                  key={request.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ delay: index * 0.05 }}
                  className="bg-white/80 backdrop-blur-md rounded-2xl p-6 shadow-sm border border-white/20 hover:shadow-md transition-shadow"
                >
                  <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                    <div className="flex-1 space-y-3">
                      <div className="flex items-center gap-3">
                        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium border ${statusConfig.color}`}>
                          <StatusIcon className="w-4 h-4" />
                          {statusConfig.label}
                        </span>
                        <span className="text-sm text-gray-400">
                          Applied on {new Date(request.created_at).toLocaleDateString()}
                        </span>
                      </div>

                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">{request.leave_type_name || 'Leave Request'}</h3>
                        <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
                          <div className="flex items-center gap-1.5">
                            <Calendar className="w-4 h-4 text-primary/60" />
                            {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()}
                          </div>
                          <div className="flex items-center gap-1.5">
                            <Clock className="w-4 h-4 text-primary/60" />
                            {request.working_days} working days
                          </div>
                        </div>
                      </div>

                      {/* Details Section */}
                      {(request.reason || request.manager_comments) && (
                        <div className="grid md:grid-cols-2 gap-4 pt-2">
                          {request.reason && (
                            <div className="bg-gray-50/50 rounded-lg p-3 text-sm">
                              <div className="font-medium text-gray-700 mb-1">Reason</div>
                              <div className="text-gray-600">{request.reason}</div>
                            </div>
                          )}
                          {request.manager_comments && (
                            <div className="bg-blue-50/50 rounded-lg p-3 text-sm border-l-2 border-blue-200">
                              <div className="font-medium text-blue-900 mb-1">Manager Comments</div>
                              <div className="text-blue-800">{request.manager_comments}</div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    {request.status === 'pending' && (
                      <div className="flex-shrink-0 pt-1">
                        <button
                          onClick={() => setCancelModal({ open: true, request, comments: '', loading: false })}
                          className="px-4 py-2 text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors border border-red-100"
                        >
                          Cancel Request
                        </button>
                      </div>
                    )}
                  </div>
                </motion.div>
              );
            })
          ) : (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-12 bg-white/50 backdrop-blur-sm rounded-2xl border border-dashed border-gray-300"
            >
              <FileText className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <h3 className="text-lg font-medium text-gray-900">No History Found</h3>
              <p className="text-gray-500">You haven't made any leave requests yet.</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Cancel Modal */}
      <AnimatePresence>
        {cancelModal.open && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/40 backdrop-blur-sm"
              onClick={() => setCancelModal({ open: false, request: null, comments: '', loading: false })}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative bg-white rounded-2xl shadow-xl w-full max-w-md p-6 overflow-hidden"
            >
              <div className="flex items-start gap-4 mb-6">
                <div className="p-3 bg-red-100 rounded-full">
                  <AlertCircle className="w-6 h-6 text-red-600" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900 font-heading">Cancel Request?</h3>
                  <p className="text-gray-600 mt-1 text-sm">
                    This action cannot be undone. The request will be removed from approval queues.
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Reason (Optional)
                  </label>
                  <textarea
                    value={cancelModal.comments}
                    onChange={(e) => setCancelModal(prev => ({ ...prev, comments: e.target.value }))}
                    className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-red-500/20 focus:border-red-500 outline-none transition-all resize-none bg-gray-50"
                    rows="3"
                    placeholder="Why are you cancelling?"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    onClick={() => setCancelModal({ open: false, request: null, comments: '', loading: false })}
                    className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg font-medium transition-colors"
                  >
                    Keep Request
                  </button>
                  <button
                    onClick={handleCancelRequest}
                    disabled={cancelModal.loading}
                    className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors shadow-lg shadow-red-600/20 disabled:opacity-50 flex items-center gap-2"
                  >
                    {cancelModal.loading ? 'Cancelling...' : 'Yes, Cancel Request'}
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default LeaveHistory;