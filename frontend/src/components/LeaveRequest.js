import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import { emitApprovalChanged } from '../utils/approvalEvents';

function LeaveRequest() {
  const [leaveTypes, setLeaveTypes] = useState([]);
  const [formData, setFormData] = useState({
    leave_type: '',
    start_date: '',
    end_date: '',
    reason: ''
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [overlapData, setOverlapData] = useState({ loading: false, overlaps: [], message: '' });
  const { user } = useAuth();

  // Helper: today's date in YYYY-MM-DD to avoid past-date submissions
  const today = new Date().toISOString().split('T')[0];
  
  // Helper: maximum allowed date (end of next year)
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

  // Debounced overlap detection
  const checkOverlaps = useCallback(
    debounce(async (startDate, endDate, deptId, userId) => {
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
        
        const overlaps = response.data.overlaps || [];
        let message = '';
        
        if (overlaps.length > 0) {
          if (overlaps.length === 1) {
            message = `⚠️ This request overlaps with ${overlaps[0].name}'s ${overlaps[0].leave_type}.`;
          } else if (overlaps.length <= 3) {
            const names = overlaps.map(o => o.name).join(', ');
            message = `⚠️ This request overlaps with leaves from ${names}.`;
          } else {
            const first = overlaps.slice(0, 2).map(o => o.name).join(', ');
            message = `⚠️ This request overlaps with leaves from ${first} and ${overlaps.length - 2} others.`;
          }
        }
        
        setOverlapData({ loading: false, overlaps, message });
        
      } catch (error) {
        console.error('Error checking overlaps:', error);
        setOverlapData({ loading: false, overlaps: [], message: '' });
      }
    }, 800), // 800ms debounce
    []
  );

  // Utility function for debouncing
  function debounce(func, delay) {
    let timeoutId;
    return function (...args) {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
  }

  // Effect to trigger overlap check when dates change
  useEffect(() => {
    if (formData.start_date && formData.end_date && user?.department?.id) {
      checkOverlaps(formData.start_date, formData.end_date, user.department.id, user.id);
    } else {
      setOverlapData({ loading: false, overlaps: [], message: '' });
    }
  }, [formData.start_date, formData.end_date, user, checkOverlaps]);

  const handleSubmit = async (e) => {
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
      emitApprovalChanged();
    } catch (error) {
      // Surface useful validation messages from API
      let text = 'Failed to submit leave request';
      const data = error.response?.data;
      if (data) {
        if (typeof data.detail === 'string') {
          text = data.detail;
        } else if (typeof data === 'object') {
          // Collect field errors (non_field_errors, start_date, end_date, leave_type, reason)
          const parts = [];
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

  const handleChange = (e) => {
    const { name, value } = e.target;

    // Guard against weekend start dates on input change
    if (name === 'start_date' && value) {
      const day = new Date(value + 'T00:00:00');
      const isWeekend = day.getUTCDay() === 6 || day.getUTCDay() === 0; // Sat=6, Sun=0 in UTC
      if (isWeekend) {
        setMessage({ type: 'error', text: 'Start date cannot be a weekend.' });
        setFormData(prev => ({ ...prev, start_date: '', end_date: prev.end_date && prev.end_date < today ? '' : prev.end_date }));
        setTimeout(() => {
          setMessage(prev => (prev.text === 'Start date cannot be a weekend.' ? { type: '', text: '' } : prev));
        }, 6000);
        return;
      }
    }

    setFormData({
      ...formData,
      [name]: value
    });
  };

  return (
    <div className="max-w-md mx-auto bg-white shadow rounded-lg">
      <div className="px-4 py-5 sm:p-6">
        <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
          Submit Leave Request
        </h3>

        {message.text && (
          <div className={`mb-4 p-4 rounded ${
            message.type === 'success' 
              ? 'bg-green-100 text-green-700 border border-green-200' 
              : 'bg-red-100 text-red-700 border border-red-200'
          }`}>
            {message.text}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="leave_type" className="block text-sm font-medium text-gray-700">
              Leave Type
            </label>
            <select
              id="leave_type"
              name="leave_type"
              value={formData.leave_type}
              onChange={handleChange}
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
            >
              <option value="">Select leave type</option>
              {Array.isArray(leaveTypes) && leaveTypes.length > 0 ? (
                leaveTypes.map((type) => (
                  <option key={type.id} value={type.id}>
                    {type.name}
                  </option>
                ))
              ) : (
                <option disabled>(No leave types found)</option>
              )}
            </select>
          </div>

          <div>
            <label htmlFor="start_date" className="block text-sm font-medium text-gray-700">
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
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              onKeyDown={(evt) => {
                // Prevent manual typing of weekend dates by blocking submission of invalid keystrokes; validation still runs on change.
                if (evt.key === 'Enter') {
                  evt.preventDefault();
                }
              }}
            />
          </div>

          <div>
            <label htmlFor="end_date" className="block text-sm font-medium text-gray-700">
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
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
            />
          </div>

          <div>
            <label htmlFor="reason" className="block text-sm font-medium text-gray-700">
              Reason (Optional)
            </label>
            <textarea
              id="reason"
              name="reason"
              rows={3}
              value={formData.reason}
              onChange={handleChange}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              placeholder="Optional reason for leave request"
            />
          </div>

          {/* Overlap Detection Advisory */}
          {(overlapData.loading || overlapData.message) && (
            <div className={`p-4 rounded-md border ${
              overlapData.loading 
                ? 'bg-blue-50 border-blue-200' 
                : overlapData.overlaps.length > 0
                  ? 'bg-yellow-50 border-yellow-200'
                  : 'bg-green-50 border-green-200'
            }`}>
              {overlapData.loading ? (
                <div className="flex items-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500 mr-2"></div>
                  <span className="text-sm text-blue-700">Checking for overlapping leaves...</span>
                </div>
              ) : (
                <div className="flex">
                  <div className="flex-shrink-0">
                    {overlapData.overlaps.length > 0 ? (
                      <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                    ) : (
                      <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                  <div className="ml-3">
                    <p className={`text-sm ${
                      overlapData.overlaps.length > 0 
                        ? 'text-yellow-700' 
                        : 'text-green-700'
                    }`}>
                      {overlapData.message || 'No overlapping leaves detected.'}
                    </p>
                    {overlapData.overlaps.length > 0 && (
                      <div className="mt-2 text-xs text-yellow-600">
                        <p>Your manager will be notified of these overlaps during the approval process.</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
            >
              {loading ? 'Submitting...' : 'Submit Request'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default LeaveRequest;