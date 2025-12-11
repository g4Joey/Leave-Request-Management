import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import api from '../services/api';
import OverlapAdvisory from './OverlapAdvisory';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, X, Clock, User, Briefcase, Calendar, FileText, ChevronLeft, ChevronRight, Search } from 'lucide-react';
import Skeleton from './common/Skeleton';

function ManagerDashboard() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [leaveRecords, setLeaveRecords] = useState([]);
  const [loadingPending, setLoadingPending] = useState(true);
  const [loadingRecords, setLoadingRecords] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [actionModal, setActionModal] = useState({ open: false, request: null, action: '', comments: '' });
  const [actingId, setActingId] = useState(null);

  useEffect(() => {
    fetchPendingApprovals();
    fetchLeaveRecords(1);
  }, []);

  const fetchPendingApprovals = async () => {
    try {
      setLoadingPending(true);
      const response = await api.get('/leaves/manager/pending_approvals/');
      setPendingApprovals(response.data.requests || response.data);
    } catch (error) {
      console.error('Error fetching pending approvals:', error);
    } finally {
      setLoadingPending(false);
    }
  };

  const fetchLeaveRecords = async (page) => {
    try {
      setLoadingRecords(true);
      const response = await api.get(`/leaves/manager/approval_records/?page=${page}`);
      const data = response.data;
      setLeaveRecords(data.results || data);
      setTotalPages(Math.ceil((data.count || 0) / 10)); // Assuming 10 items per page
      setCurrentPage(page);
    } catch (error) {
      console.error('Error fetching leave records:', error);
    } finally {
      setLoadingRecords(false);
    }
  };

  const handleAction = async () => {
    const { request, action, comments } = actionModal;
    if (!request) return;

    try {
      setActingId(request.id);
      if (action === 'approve') {
        await api.put(`/leaves/manager/${request.id}/approve/`, { approval_comments: comments });
        showToast({ type: 'success', message: 'Leave request approved successfully.' });
      } else if (action === 'reject') {
        await api.put(`/leaves/manager/${request.id}/reject/`, { rejection_comments: comments });
        showToast({ type: 'success', message: 'Leave request rejected successfully.' });
      }
      
      await fetchPendingApprovals();
      fetchLeaveRecords(currentPage); // Refresh records to show new status
      setActionModal({ open: false, request: null, action: '', comments: '' });
    } catch (error) {
      console.error(`Error ${action}ing request:`, error);
      showToast({ type: 'error', message: `Failed to ${action} request` });
    } finally {
      setActingId(null);
    }
  };

  const openActionModal = (request, action) => {
    setActionModal({ open: true, request, action, comments: '' });
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 font-heading">Manager Dashboard</h1>
        <p className="text-gray-500 mt-1">Manage team leave requests and view history</p>
      </div>

      {/* Pending Approvals */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
           <div className="w-2 h-6 bg-primary rounded-full"></div>
           Pending Approvals
           {pendingApprovals.length > 0 && (
              <span className="bg-primary/10 text-primary text-xs px-2 py-0.5 rounded-full">{pendingApprovals.length}</span>
           )}
        </h2>
        
        {loadingPending ? (
           <div className="space-y-4">
              {[1, 2].map(i => <Skeleton key={i} className="h-48 w-full rounded-xl" />)}
           </div>
        ) : pendingApprovals.length === 0 ? (
           <div className="text-center py-12 bg-white/60 backdrop-blur-sm rounded-2xl border border-dashed border-gray-300">
              <Check className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <h3 className="text-gray-900 font-medium">All caught up!</h3>
              <p className="text-gray-500 text-sm">No pending requests for your review.</p>
           </div>
        ) : (
           <AnimatePresence>
              {pendingApprovals.map((request) => (
                <motion.div
                  key={request.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="bg-white/80 backdrop-blur-md rounded-xl p-6 shadow-sm border border-white/20"
                >
                  <OverlapAdvisory 
                     leaveRequest={{
                        ...request,
                        employee_department_id: request.employee_department_id || request.department_id,
                        employee_id: request.employee_id || request.employee
                     }}
                     className="mb-4"
                  />
                  
                  <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="h-10 w-10 bg-primary/10 rounded-full flex items-center justify-center text-primary font-bold text-sm">
                           {request.employee_name?.[0]}
                        </div>
                        <div>
                          <h3 className="font-semibold text-gray-900">{request.employee_name}</h3>
                          <div className="flex items-center gap-2 text-xs text-gray-500">
                             <Briefcase className="w-3 h-3" /> {request.employee_department || 'Department'}
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4 mt-4 bg-gray-50/50 p-4 rounded-lg border border-gray-100/50">
                         <div>
                            <div className="text-xs text-gray-500 mb-1 flex items-center gap-1"><FileText className="w-3 h-3"/> Leave Type</div>
                            <div className="font-medium text-gray-900">{request.leave_type_name}</div>
                         </div>
                         <div>
                            <div className="text-xs text-gray-500 mb-1 flex items-center gap-1"><Clock className="w-3 h-3"/> Duration</div>
                            <div className="font-medium text-gray-900">{request.total_days} Days</div>
                            <div className="text-xs text-gray-500">
                               {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()}
                            </div>
                         </div>
                      </div>

                      {request.reason && (
                         <div className="mt-4 text-sm bg-white p-3 rounded border border-gray-100">
                            <span className="font-medium text-gray-700 block mb-1">Reason:</span>
                            <span className="text-gray-600">{request.reason}</span>
                         </div>
                      )}
                    </div>

                    <div className="flex md:flex-col gap-3 justify-end md:justify-start">
                       <button
                         onClick={() => openActionModal(request, 'approve')}
                         disabled={actingId === request.id}
                         className="flex items-center justify-center gap-2 px-4 py-2.5 bg-primary text-white rounded-lg hover:bg-primary-hover shadow-lg shadow-primary/20 transition-all font-medium min-w-[120px]"
                       >
                         {actingId === request.id ? 'Processing...' : <><Check className="w-4 h-4"/> Approve</>}
                       </button>
                       <button
                         onClick={() => openActionModal(request, 'reject')}
                         disabled={actingId === request.id}
                         className="flex items-center justify-center gap-2 px-4 py-2.5 bg-white border border-red-200 text-red-600 rounded-lg hover:bg-red-50 transition-all font-medium min-w-[120px]"
                       >
                         <X className="w-4 h-4"/> Reject
                       </button>
                    </div>
                  </div>
                </motion.div>
              ))}
           </AnimatePresence>
        )}
      </div>

      {/* History Records */}
      <div className="pt-8 border-t border-gray-200">
         <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
               <Clock className="w-5 h-5 text-gray-400" /> Approval History
            </h2>
         </div>
         
         {loadingRecords ? (
            <div className="space-y-3">
               {[1, 2, 3].map(i => <Skeleton key={i} className="h-20 w-full" />)}
            </div>
         ) : leaveRecords.length === 0 ? (
            <div className="text-center py-12 text-gray-400">No approval history found.</div>
         ) : (
            <div className="space-y-2">
               {leaveRecords.map(record => (
                 <div key={record.id} className="flex items-center justify-between p-4 bg-white rounded-lg border border-gray-100 text-sm hover:bg-gray-50 transition-colors">
                    <div className="flex items-center gap-3">
                       <div className={`w-2 h-2 rounded-full ${['approved','manager_approved','hr_approved'].includes(record.status) ? 'bg-green-500' : record.status === 'rejected' ? 'bg-red-500' : 'bg-gray-400'}`} />
                       <div>
                          <div className="font-medium text-gray-900">{record.employee_name}</div>
                          <div className="text-gray-500 text-xs">{record.leave_type_name} • {record.total_days} days</div>
                       </div>
                    </div>
                    <div className="text-right text-xs text-gray-400">
                       {new Date(record.created_at).toLocaleDateString()}
                       <div className={`mt-1 font-medium ${['approved','manager_approved','hr_approved'].includes(record.status) ? 'text-green-600' : record.status === 'rejected' ? 'text-red-600' : 'text-gray-500'}`}>
                          {record.status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                       </div>
                    </div>
                 </div>
               ))}
               
               {/* Pagination */}
               <div className="flex justify-center gap-2 mt-6">
                  <button 
                     disabled={currentPage === 1}
                     onClick={() => fetchLeaveRecords(currentPage - 1)}
                     className="p-2 rounded-lg border border-gray-200 disabled:opacity-50 hover:bg-gray-50"
                  >
                     <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="flex items-center px-4 text-sm font-medium text-gray-600">
                     Page {currentPage} of {totalPages}
                  </span>
                  <button 
                     disabled={currentPage === totalPages}
                     onClick={() => fetchLeaveRecords(currentPage + 1)}
                     className="p-2 rounded-lg border border-gray-200 disabled:opacity-50 hover:bg-gray-50"
                  >
                     <ChevronRight className="w-4 h-4" />
                  </button>
               </div>
            </div>
         )}
      </div>

      {/* Action Modal */}
      <AnimatePresence>
         {actionModal.open && (
           <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
             <motion.div
               initial={{ opacity: 0 }}
               animate={{ opacity: 1 }}
               exit={{ opacity: 0 }}
               className="absolute inset-0 bg-black/40 backdrop-blur-sm"
               onClick={() => setActionModal({ open: false, request: null, action: '', comments: '' })}
             />
             <motion.div 
               initial={{ scale: 0.95, opacity: 0 }}
               animate={{ scale: 1, opacity: 1 }}
               exit={{ scale: 0.95, opacity: 0 }}
               className="relative bg-white rounded-xl shadow-xl p-6 w-full max-w-md"
             >
                <h3 className="text-lg font-bold text-gray-900 mb-2">
                   {actionModal.action === 'approve' ? 'Approve Request' : 'Reject Request'}
                </h3>
                <p className="text-gray-500 text-sm mb-4">
                   Are you sure you want to {actionModal.action} this request for {actionModal.request?.employee_name}?
                </p>
                <div className="mb-4">
                   <label className="block text-sm font-medium text-gray-700 mb-2">
                      Comments (Optional)
                   </label>
                   <textarea
                      value={actionModal.comments}
                      onChange={(e) => setActionModal(prev => ({ ...prev, comments: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary/20 outline-none min-h-[100px]"
                      rows="3"
                      placeholder="Add comments..."
                   />
                </div>
                <div className="flex justify-end gap-3">
                   <button 
                      onClick={() => setActionModal({ open: false, request: null, action: '', comments: '' })}
                      className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 rounded-lg"
                   >
                      Cancel
                   </button>
                   <button 
                      onClick={handleAction}
                      className={`px-4 py-2 text-sm text-white rounded-lg ${actionModal.action === 'approve' ? 'bg-primary hover:bg-primary-hover' : 'bg-red-600 hover:bg-red-700'}`}
                   >
                      Confirm
                   </button>
                </div>
             </motion.div>
           </div>
         )}
      </AnimatePresence>
    </div>
  );
}

export default ManagerDashboard;