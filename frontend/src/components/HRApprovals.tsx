import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import api from '../services/api';
import OverlapAdvisory from './OverlapAdvisory';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, X, Clock, User, Briefcase, Calendar, FileText, ChevronRight, Building } from 'lucide-react';
import Skeleton from './common/Skeleton';

function HRApprovals() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [pendingApprovals, setPendingApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [actionModal, setActionModal] = useState({ open: false, action: '', comments: '' });
  const [actingId, setActingId] = useState(null);
  const [groupedApprovals, setGroupedApprovals] = useState<any>({});
  const [activeTab, setActiveTab] = useState('Merban Capital');
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [recordsGroups, setRecordsGroups] = useState<any>({ 'Merban Capital': [], 'SDSL': [], 'SBL': [] });
  const [recordsActiveTab, setRecordsActiveTab] = useState('Merban Capital');

  useEffect(() => {
    fetchPendingApprovals();
    fetchApprovalRecords();
  }, []);

  const fetchPendingApprovals = async () => {
    try {
      setLoading(true);
      const response = await api.get('/leaves/manager/pending_approvals/?stage=hr');
      const requests = response.data.requests || [];
      setPendingApprovals(requests);
      
      const grouped = requests.reduce((acc: any, request: any) => {
        const affiliate = getEmployeeAffiliate(request);
        if (!acc[affiliate]) {
          acc[affiliate] = [];
        }
        acc[affiliate].push(request);
        return acc;
      }, {});
      
      setGroupedApprovals(grouped);
      const orderedKeys = ['Merban Capital', 'SDSL', 'SBL'];
      const firstWithItems = orderedKeys.find(k => (grouped[k] || []).length > 0);
      if (firstWithItems) setActiveTab(firstWithItems);
    } catch (error) {
      console.error('Error fetching pending approvals:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchApprovalRecords = async () => {
    try {
      setRecordsLoading(true);
      const res = await api.get('/leaves/manager/approval_records/', { params: { ordering: '-created_at', limit: 50 } });
      const groups = (res.data && res.data.groups) || {};
      setRecordsGroups({
        'Merban Capital': groups['Merban Capital'] || [],
        'SDSL': groups['SDSL'] || [],
        'SBL': groups['SBL'] || [],
      });
      const orderedKeys = ['Merban Capital', 'SDSL', 'SBL'];
      const firstWithItems = orderedKeys.find(k => (groups[k] || []).length > 0) || 'Merban Capital';
      setRecordsActiveTab(firstWithItems);
    } catch (e) {
      console.error('Error fetching HR approval records:', e);
      setRecordsGroups({ 'Merban Capital': [], 'SDSL': [], 'SBL': [] });
    } finally {
      setRecordsLoading(false);
    }
  };

  const getEmployeeAffiliate = (request) => {
    const raw = request.employee_department_affiliate || request.employee_affiliate || request.affiliate || '';
    const name = (raw || '').toString().trim();
    if (!name) return 'Other';
    if (/^merban(\s+capital)?$/i.test(name) || /^merban\s*capital$/i.test(name) || name.toUpperCase() === 'MERBAN CAPITAL') {
      return 'Merban Capital';
    }
    if (name.toUpperCase() === 'SDSL') return 'SDSL';
    if (name.toUpperCase() === 'SBL') return 'SBL';
    return name;
  };

  const handleAction = async (requestId, action, comments = '') => {
    try {
      setActingId(requestId);
      if (action === 'approve') {
        await api.put(`/leaves/manager/${requestId}/approve/`, { approval_comments: comments });
        showToast({ type: 'success', message: 'Leave request approved successfully.' });
      } else if (action === 'reject') {
        await api.put(`/leaves/manager/${requestId}/reject/`, { rejection_comments: comments });
        showToast({ type: 'success', message: 'Leave request rejected successfully.' });
      }
      
      await fetchPendingApprovals();
      setActionModal({ open: false, action: '', comments: '' });
      setSelectedRequest(null);
    } catch (error) {
      console.error(`Error ${action}ing request:`, error);
      showToast({ type: 'error', message: `Failed to ${action} request` });
    } finally {
      setActingId(null);
    }
  };

  const openActionModal = (request, action) => {
    setSelectedRequest(request);
    setActionModal({ open: true, action, comments: '' });
  };

  const tabs = [
    { key: 'Merban Capital', label: 'Merban Capital', count: (groupedApprovals['Merban Capital'] || []).length },
    { key: 'SDSL', label: 'SDSL', count: (groupedApprovals['SDSL'] || []).length },
    { key: 'SBL', label: 'SBL', count: (groupedApprovals['SBL'] || []).length },
  ];

  if (loading) {
     return (
        <div className="space-y-6 max-w-5xl mx-auto">
           <Skeleton className="h-12 w-48 mb-4" />
           <div className="grid grid-cols-3 gap-4 mb-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
           </div>
           {[1,2,3].map(i => <Skeleton key={i} className="h-48 w-full rounded-xl" />)}
        </div>
     )
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 font-heading">HR Approvals</h1>
        <p className="text-gray-500 mt-1">Review finalized requests pending HR sign-off</p>
      </div>

      {/* Tabs */}
      <div className="flex p-1 space-x-1 bg-gray-100/50 rounded-xl backdrop-blur-sm">
        {tabs.map((tab) => {
           const isActive = activeTab === tab.key;
           return (
             <button
               key={tab.key}
               onClick={() => setActiveTab(tab.key)}
               className={`
                 relative flex-1 flex items-center justify-center py-2.5 text-sm font-medium rounded-lg transition-all
                 ${isActive ? 'text-gray-900' : 'text-gray-500 hover:text-gray-700'}
               `}
             >
               {isActive && (
                 <motion.div
                   layoutId="activeTabBg"
                   className="absolute inset-0 bg-white shadow-sm rounded-lg"
                   transition={{ type: "spring", stiffness: 500, damping: 30 }}
                 />
               )}
               <span className="relative z-10 flex items-center gap-2">
                 {tab.label}
                 {tab.count > 0 && (
                   <span className={`px-2 py-0.5 text-xs rounded-full ${isActive ? 'bg-primary/10 text-primary' : 'bg-gray-200 text-gray-600'}`}>
                     {tab.count}
                   </span>
                 )}
               </span>
             </button>
           );
        })}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
           key={activeTab}
           initial={{ opacity: 0, x: 10 }}
           animate={{ opacity: 1, x: 0 }}
           exit={{ opacity: 0, x: -10 }}
           transition={{ duration: 0.2 }}
        >
          {(groupedApprovals[activeTab] || []).length === 0 ? (
            <div className="text-center py-16 bg-white/60 backdrop-blur-sm rounded-2xl border border-dashed border-gray-300">
              <Check className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <h3 className="text-gray-900 font-medium">All caught up!</h3>
              <p className="text-gray-500 text-sm">No pending requests for {activeTab}</p>
            </div>
          ) : (
            <div className="space-y-4">
              {(groupedApprovals[activeTab] || []).map((request) => (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  key={request.id} 
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
                          <h3 className="font-semibold text-gray-900">{request.employee_name || 'Employee'}</h3>
                          <div className="flex items-center gap-2 text-xs text-gray-500">
                             <Briefcase className="w-3 h-3" /> {request.employee_department} 
                             <span className="text-gray-300">|</span> 
                             <Building className="w-3 h-3" /> {getEmployeeAffiliate(request)}
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
                            <span className="font-medium text-gray-700 block mb-1">Employee Reason:</span>
                            <span className="text-gray-600">{request.reason}</span>
                         </div>
                      )}
                      
                      {request.manager_approval_comments && (
                        <div className="mt-2 text-sm bg-green-50 p-3 rounded border border-green-100">
                            <span className="font-medium text-green-800 block mb-1">Manager Comments:</span>
                            <span className="text-green-700">{request.manager_approval_comments}</span>
                        </div>
                      )}
                    </div>

                    <div className="flex md:flex-col gap-3 justify-end md:justify-start">
                       <button
                         onClick={() => handleAction(request.id, 'approve')}
                         disabled={actingId === request.id}
                         className="flex items-center justify-center gap-2 px-4 py-2.5 bg-primary text-white rounded-lg hover:bg-primary-hover shadow-lg shadow-primary/20 transition-all font-medium min-w-[120px]"
                       >
                         {actingId === request.id ? 'Approving...' : <><Check className="w-4 h-4"/> Approve</>}
                       </button>
                       <button
                         onClick={() => openActionModal(request, 'reject')}
                         className="flex items-center justify-center gap-2 px-4 py-2.5 bg-white border border-red-200 text-red-600 rounded-lg hover:bg-red-50 transition-all font-medium min-w-[120px]"
                       >
                         <X className="w-4 h-4"/> Reject
                       </button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {/* History Section */}
      <div className="pt-8 border-t border-gray-200">
         <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-gray-400" /> Recent History
         </h2>
         
         <div className="flex p-1 space-x-1 bg-gray-100 rounded-lg w-max mb-6">
            {['Merban Capital', 'SDSL', 'SBL'].map(key => (
               <button
                  key={key}
                  onClick={() => setRecordsActiveTab(key)}
                  className={`px-4 py-1.5 text-xs font-medium rounded-md transition-all ${recordsActiveTab === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
               >
                  {key}
               </button>
            ))}
         </div>
         
         {recordsLoading ? (
            <div className="space-y-3">
               {[1,2].map(i => <Skeleton key={i} className="h-20 w-full" />)}
            </div>
         ) : (
            <div className="space-y-2">
               {(recordsGroups[recordsActiveTab] || []).length === 0 ? (
                  <div className="text-gray-400 text-sm text-center py-4">No records found.</div>
               ) : (
                  (recordsGroups[recordsActiveTab] || []).map(record => (
                     <div key={record.id} className="flex items-center justify-between p-4 bg-white rounded-lg border border-gray-100 text-sm">
                        <div className="flex items-center gap-3">
                           <div className={`w-2 h-2 rounded-full ${record.status === 'approved' ? 'bg-green-500' : 'bg-red-500'}`} />
                           <div>
                              <div className="font-medium text-gray-900">{record.employee_name}</div>
                              <div className="text-gray-500 text-xs">{record.leave_type_name} • {record.total_days} days</div>
                           </div>
                        </div>
                        <div className="text-right text-xs text-gray-400">
                           {new Date(record.created_at).toLocaleDateString()}
                           <div className={`mt-1 font-medium ${record.status === 'approved' ? 'text-green-600' : 'text-red-600'}`}>
                              {record.status === 'approved' ? 'Approved' : 'Rejected'}
                           </div>
                        </div>
                     </div>
                  ))
               )}
            </div>
         )}
      </div>

      {/* Modal */}
      <AnimatePresence>
         {actionModal.open && (
           <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
             <motion.div
               initial={{ opacity: 0 }}
               animate={{ opacity: 1 }}
               exit={{ opacity: 0 }}
               className="absolute inset-0 bg-black/40 backdrop-blur-sm"
               onClick={() => setActionModal({ open: false, action: '', comments: '' })}
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
                   Add optional comments for the employee.
                </p>
                <textarea
                   className="w-full border border-gray-200 rounded-lg p-3 text-sm focus:ring-2 focus:ring-primary/20 outline-none mb-4 min-h-[100px]"
                   placeholder="Add comments..."
                   value={actionModal.comments}
                   onChange={e => setActionModal(prev => ({ ...prev, comments: e.target.value }))}
                />
                <div className="flex justify-end gap-3">
                   <button 
                      onClick={() => setActionModal({ open: false, action: '', comments: '' })}
                      className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 rounded-lg"
                   >
                      Cancel
                   </button>
                   <button 
                      onClick={() => handleAction(selectedRequest.id, actionModal.action, actionModal.comments)}
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

export default HRApprovals;