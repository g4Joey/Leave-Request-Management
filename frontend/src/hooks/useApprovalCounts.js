import { useState, useEffect } from 'react';
import api from '../services/api';

export const useApprovalCounts = () => {
  const [counts, setCounts] = useState({
    manager_approvals: 0,
    hr_approvals: 0,
    ceo_approvals: 0,
    recall_pending: 0,
    total: 0
  });
  const [loading, setLoading] = useState(true);

  const fetchCounts = async () => {
    try {
      // Pull approval counts and recall counts together so badges stay in sync for staff.
      const [approvalRes, recallRes] = await Promise.all([
        api.get('/leaves/manager/approval_counts/'),
        api.get('/leaves/manager/pending_recall_count/').catch(() => ({ data: { recall_pending: 0 } }))
      ]);
      const approvalData = approvalRes?.data || {};
      const recallData = recallRes?.data || {};
      setCounts({
        ...approvalData,
        recall_pending: recallData.recall_pending || 0,
        total: approvalData.total || 0
      });
    } catch (error) {
      console.error('Error fetching approval counts:', error);
      // Keep default counts on error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCounts();
    
    // Refresh counts every 30 seconds
    const interval = setInterval(fetchCounts, 30000);
    // Also refresh immediately when approval actions occur elsewhere
    const onChanged = () => fetchCounts();
    window.addEventListener('approval:changed', onChanged);
    
    return () => {
      clearInterval(interval);
      window.removeEventListener('approval:changed', onChanged);
    };
  }, []);

  return { counts, loading, refreshCounts: fetchCounts };
};