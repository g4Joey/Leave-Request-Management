import React, { useState, useEffect } from 'react';
import api from '../services/api';

function OverlapAdvisory({ leaveRequest, onDismiss, className = '' }) {
  const [overlapData, setOverlapData] = useState({ loading: false, overlaps: [], message: '' });
  const [isDismissed, setIsDismissed] = useState(false);

  useEffect(() => {
    if (!leaveRequest || !leaveRequest.employee_department_id || isDismissed) return;

    const fetchOverlaps = async () => {
      try {
        setOverlapData(prev => ({ ...prev, loading: true }));
        
        const response = await api.get('/leaves/overlaps/', {
          params: {
            start: leaveRequest.start_date,
            end: leaveRequest.end_date,
            dept_id: leaveRequest.employee_department_id || leaveRequest.department_id,
            exclude_user_id: leaveRequest.employee_id || leaveRequest.employee
          }
        });
        
        const overlaps = response.data.overlaps || [];
        let message = '';
        
        if (overlaps.length > 0) {
          if (overlaps.length === 1) {
            message = `This request overlaps with ${overlaps[0].name}'s ${overlaps[0].leave_type} leave (${overlaps[0].start_date} to ${overlaps[0].end_date}).`;
          } else if (overlaps.length <= 3) {
            const details = overlaps.map(o => `${o.name} (${o.start_date} to ${o.end_date})`).join(', ');
            message = `This request overlaps with leaves from: ${details}.`;
          } else {
            const first = overlaps.slice(0, 2).map(o => `${o.name}`).join(', ');
            message = `This request overlaps with leaves from ${first} and ${overlaps.length - 2} other department members.`;
          }
        }
        
        setOverlapData({ loading: false, overlaps, message });
        
      } catch (error) {
        console.error('Error fetching overlap data:', error);
        setOverlapData({ loading: false, overlaps: [], message: '' });
      }
    };

    fetchOverlaps();
  }, [leaveRequest, isDismissed]);

  const handleDismiss = () => {
    setIsDismissed(true);
    if (onDismiss) {
      onDismiss();
    }
  };

  if (isDismissed || overlapData.loading || !overlapData.message) {
    return null;
  }

  return (
    <div className={`mb-4 p-4 rounded-md border border-amber-200 bg-amber-50 ${className}`}>
      <div className="flex">
        <div className="flex-shrink-0">
          <svg className="h-5 w-5 text-amber-400" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        </div>
        <div className="ml-3 flex-1">
          <h3 className="text-sm font-medium text-amber-800">
            Department Leave Overlap Detected
          </h3>
          <div className="mt-2 text-sm text-amber-700">
            <p>{overlapData.message}</p>
            {overlapData.overlaps.length > 0 && (
              <div className="mt-2 text-xs">
                <p className="font-medium">Consider:</p>
                <ul className="ml-4 list-disc">
                  <li>Staffing coverage during overlapping periods</li>
                  <li>Project deadlines and deliverables</li>
                  <li>Alternative leave dates if possible</li>
                </ul>
              </div>
            )}
          </div>
        </div>
        <div className="ml-auto pl-3">
          <div className="-mx-1.5 -my-1.5">
            <button
              type="button"
              onClick={handleDismiss}
              className="inline-flex rounded-md bg-amber-50 p-1.5 text-amber-500 hover:bg-amber-100 focus:outline-none focus:ring-2 focus:ring-amber-600 focus:ring-offset-2 focus:ring-offset-amber-50"
            >
              <span className="sr-only">Dismiss</span>
              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default OverlapAdvisory;