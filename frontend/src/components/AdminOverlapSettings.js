import React, { useState, useEffect } from 'react';
import api from '../services/api';

function AdminOverlapSettings() {
  const [minDays, setMinDays] = useState(2);
  const [enabled, setEnabled] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const min = 1, max = 20;

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        setLoading(true);
        const res = await api.get('/notifications/settings/overlap/');
        setMinDays(res.data.min_days ?? 2);
        setEnabled(Boolean(res.data.enabled));
      } catch (err) {
        setError('Failed to load overlap settings');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError('');
      setSuccess('');
      await api.put('/notifications/settings/overlap/', { min_days: minDays, enabled });
      setSuccess('Settings saved');
    } catch (err) {
      setError('Failed to save settings');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-32">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">Overlap Notification Settings</h3>
      <p className="text-sm text-gray-600 mb-6">Configure the minimum overlapping days before managers are notified to reduce alert fatigue.</p>

      {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded">{error}</div>}
      {success && <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded">{success}</div>}

      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Minimum overlapping days: <span className="font-semibold">{minDays}</span>
        </label>
        <input
          type="range"
          min={min}
          max={max}
          value={minDays}
          onChange={(e) => setMinDays(parseInt(e.target.value, 10))}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-gray-500">
          <span>{min}</span>
          <span>{max}</span>
        </div>
      </div>

      <div className="mb-6">
        <label className="inline-flex items-center">
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} className="mr-2" />
          <span>Enable overlap detection</span>
        </label>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}

export default AdminOverlapSettings;
