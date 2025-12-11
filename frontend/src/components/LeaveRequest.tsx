import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import { Calendar, FileText, AlertTriangle, CheckCircle, Clock } from 'lucide-react';

interface LeaveType {
  id: number;
  name: string;
}

interface Overlap {
  name: string;
  leave_type: string;
}

interface OverlapData {
  loading: boolean;
  overlaps: Overlap[];
  message: string;
}

interface LeaveRequestData {
  leave_type: string;
  start_date: string;
  end_date: string;
  reason: string;
}

function LeaveRequest() {
  const [leaveTypes, setLeaveTypes] = useState<LeaveType[]>([]);
  const [formData, setFormData] = useState<LeaveRequestData>({
    leave_type: '',
    start_date: '',
    end_date: '',
    reason: ''
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [overlapData, setOverlapData] = useState<OverlapData>({ loading: false, overlaps: [], message: '' });
  const { user } = useAuth();

  const today = new Date().toISOString().split('T')[0];
  const maxDate = new Date(new Date().getFullYear() + 1, 11, 31).toISOString().split('T')[0];

  useEffect(() => {
    const fetchLeaveTypes = async () => {
      try {
        const response = await api.get('/leaves/types/');
        setLeaveTypes(response.data.results || response.data);
      } catch (error) {
        console.error('Error fetching leave types:', error);
      }
    };

    fetchLeaveTypes();
  }, []);

  const checkOverlaps = useCallback(
    debounce(async (startDate: string, endDate: string, deptId: number, userId: number) => {
      if (!startDate || !endDate || !deptId) return;
      
      try {
        setOverlapData(prev => ({ ...prev, loading: true }));
        
        const response = await api.get('/leaves/overlaps/', {
          params: {
            start: startDate,
            end: endDate,
            dept_id: deptId,
            exclude_user_id: userId
          }
        });
        
        const overlaps: Overlap[] = response.data.overlaps || [];
        let msg = '';
        
        if (overlaps.length > 0) {
          if (overlaps.length === 1) {
            msg = `⚠️ Overlaps with ${overlaps[0].name}'s ${overlaps[0].leave_type} leave.`;
          } else if (overlaps.length <= 3) {
            const names = overlaps.map(o => o.name).join(', ');
            msg = `⚠️ Overlaps with leaves from ${names}.`;
          } else {
            const first = overlaps.slice(0, 2).map(o => o.name).join(', ');
            msg = `⚠️ Overlaps with leaves from ${first} and ${overlaps.length - 2} others.`;
          }
        }
        
        setOverlapData({ loading: false, overlaps, message: msg });
        
      } catch (error) {
        console.error('Error checking overlaps:', error);
        setOverlapData({ loading: false, overlaps: [], message: '' });
      }
    }, 800),
    []
  );

  // eslint-disable-next-line react-hooks/exhaustive-deps
  function debounce<T extends (...args: any[]) => void>(func: T, delay: number) {
    let timeoutId: ReturnType<typeof setTimeout>;
    return function (this: any, ...args: Parameters<T>) {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
  }

  useEffect(() => {
    if (formData.start_date && formData.end_date && user?.department?.id) {
      checkOverlaps(formData.start_date, formData.end_date, user.department.id, user.id);
    } else {
      setOverlapData({ loading: false, overlaps: [], message: '' });
    }
  }, [formData.start_date, formData.end_date, user, checkOverlaps]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ type: '', text: '' });

    try {
      await api.post('/leaves/requests/', formData);
      setMessage({ type: 'success', text: 'Leave request submitted successfully!' });
      setFormData({
        leave_type: '',
        start_date: '',
        end_date: '',
        reason: ''
      });
    } catch (error: any) {
      let text = 'Failed to submit leave request';
      const data = error.response?.data;
      if (data) {
        if (typeof data.detail === 'string') {
          text = data.detail;
        } else if (typeof data === 'object') {
          const parts: string[] = [];
          Object.entries(data).forEach(([key, val]) => {
            const messages = Array.isArray(val) ? val.join(' ') : String(val);
            parts.push(`${key.replace(/_/g, ' ')}: ${messages}`);
          });
          if (parts.length) {
            text = parts.join(' | ');
          }
        }
      }
      setMessage({ type: 'error', text });
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in text-left">
      <div className="glass-panel rounded-2xl p-8">
        <div className="flex items-center gap-4 mb-8">
          <div className="bg-primary/5 p-3 rounded-xl">
             <Calendar className="w-8 h-8 text-primary" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-primary font-heading">New Leave Request</h2>
            <p className="text-gray-500">Submit a new request for time off.</p>
          </div>
        </div>

        {message.text && (
          <div className={`mb-6 p-4 rounded-xl flex items-start gap-3 ${
            message.type === 'success' 
              ? 'bg-green-50 text-green-800 border border-green-100' 
              : 'bg-red-50 text-red-800 border border-red-100'
          }`}>
             {message.type === 'success' ? <CheckCircle className="w-5 h-5 mt-0.5" /> : <AlertTriangle className="w-5 h-5 mt-0.5" />}
             <div>
               <p className="font-semibold">{message.type === 'success' ? 'Success' : 'Error'}</p>
               <p className="text-sm opacity-90">{message.text}</p>
             </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
             <div className="col-span-1 md:col-span-2">
                <label htmlFor="leave_type" className="block text-sm font-semibold text-gray-700 mb-2">
                  Leave Type
                </label>
                <div className="relative">
                  <select
                    id="leave_type"
                    name="leave_type"
                    value={formData.leave_type}
                    onChange={handleChange}
                    required
                    className="input-field appearance-none"
                  >
                    <option value="">Select a leave type...</option>
                    {leaveTypes.map((type) => (
                      <option key={type.id} value={type.id}>
                        {type.name}
                      </option>
                    ))}
                  </select>
                  <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                  </div>
                </div>
             </div>

             <div>
                <label htmlFor="start_date" className="block text-sm font-semibold text-gray-700 mb-2">
                  Start Date
                </label>
                <input
                  type="date"
                  id="start_date"
                  name="start_date"
                  value={formData.start_date}
                  onChange={handleChange}
                  required
                  min={today}
                  max={maxDate}
                  className="input-field"
                />
             </div>

             <div>
                <label htmlFor="end_date" className="block text-sm font-semibold text-gray-700 mb-2">
                  End Date
                </label>
                <input
                  type="date"
                  id="end_date"
                  name="end_date"
                  value={formData.end_date}
                  onChange={handleChange}
                  required
                  min={formData.start_date || today}
                  max={maxDate}
                  className="input-field"
                />
             </div>
          </div>

          <div>
            <label htmlFor="reason" className="block text-sm font-semibold text-gray-700 mb-2">
              Reason <span className="text-gray-400 font-normal">(Optional)</span>
            </label>
            <div className="relative">
              <textarea
                id="reason"
                name="reason"
                rows={3}
                value={formData.reason}
                onChange={handleChange}
                className="input-field pl-10 pt-3"
                placeholder="e.g. Family vacation, Medical appointment..."
              />
              <FileText className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
            </div>
          </div>

          {/* Overlap Detection Advisory */}
          {(overlapData.loading || overlapData.message) && (
            <div className={`p-4 rounded-xl border flex items-start gap-3 transition-colors duration-300 ${
              overlapData.loading 
                ? 'bg-blue-50 border-blue-100 text-blue-700' 
                : overlapData.overlaps.length > 0
                  ? 'bg-yellow-50 border-yellow-100 text-yellow-800'
                  : 'bg-green-50 border-green-100 text-green-700'
            }`}>
              {overlapData.loading ? (
                 <Clock className="w-5 h-5 animate-spin" />
              ) : overlapData.overlaps.length > 0 ? (
                 <AlertTriangle className="w-5 h-5" />
              ) : (
                 <CheckCircle className="w-5 h-5" />
              )}
              
              <div className="flex-1">
                 <p className="font-medium text-sm">
                   {overlapData.loading ? 'Checking for schedule conflicts...' : (overlapData.message || 'No overlapping leaves detected.')}
                 </p>
                 {!overlapData.loading && overlapData.overlaps.length > 0 && (
                   <p className="text-xs mt-1 opacity-80">Your manager will be notified of these overlaps.</p>
                 )}
              </div>
            </div>
          )}

          <div className="pt-4">
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex justify-center items-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Submitting...</span>
                </>
              ) : (
                <>
                  <span>Submit Application</span>
                  <CheckCircle className="w-5 h-5" />
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default LeaveRequest;