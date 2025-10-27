import { useState, useEffect } from 'react';
import api from '../services/api';

export const useApprovalCounts = () => {
  const [counts, setCounts] = useState({
    manager_approvals: 0,
    hr_approvals: 0,
    ceo_approvals: 0,
    total: 0
  });
  const [loading, setLoading] = useState(true);

  const fetchCounts = async () => {
    try {
      const response = await api.get('/leaves/approval_counts/');
      setCounts(response.data);
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
    
    return () => clearInterval(interval);
  }, []);

  return { counts, loading, refreshCounts: fetchCounts };
};