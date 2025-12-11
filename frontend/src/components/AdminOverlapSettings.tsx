import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Save, AlertTriangle, CheckCircle, Sliders } from 'lucide-react';

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
      setSuccess('Settings saved successfully');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Unknown error';
      setError(`Failed to save settings: ${detail}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-48">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div className="flex items-start gap-4">
        <div className="p-3 bg-amber-50 text-amber-600 rounded-xl">
           <Sliders className="w-6 h-6" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-gray-900">Overlap Notification Settings</h3>
          <p className="text-sm text-gray-500">
            Configure the minimum overlapping days before managers are notified. This helps reduce alert fatigue for short overlaps.
          </p>
        </div>
      </div>

      <AnimatePresence>
        {error && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="p-4 bg-red-50/50 border border-red-200 rounded-xl flex items-center gap-3 text-red-700">
             <AlertTriangle className="w-5 h-5" />
             {error}
          </motion.div>
        )}
        {success && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="p-4 bg-green-50/50 border border-green-200 rounded-xl flex items-center gap-3 text-green-700">
             <CheckCircle className="w-5 h-5" />
             {success}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="bg-white/50 rounded-xl p-6 border border-gray-100 space-y-8">
        <div>
          <div className="flex justify-between items-center mb-4">
            <label className="text-sm font-medium text-gray-700">
              Minimum Overlapping Days
            </label>
            <span className="px-3 py-1 bg-primary/10 text-primary font-bold rounded-lg text-sm">
               {minDays} Days
            </span>
          </div>
          
          <div className="relative pt-1">
             <input
               type="range"
               min={min}
               max={max}
               value={minDays}
               onChange={(e) => setMinDays(parseInt(e.target.value, 10))}
               className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary"
             />
             <div className="flex justify-between text-xs text-gray-400 mt-2">
               <span>{min} Day</span>
               <span>{max} Days</span>
             </div>
          </div>
        </div>

        <div className="flex items-center justify-between pt-4 border-t border-gray-100">
          <div>
            <span className="block text-sm font-medium text-gray-700">Enable Detection</span>
            <span className="text-xs text-gray-500">Toggle the overlap advisory system on or off</span>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input 
              type="checkbox" 
              checked={enabled} 
              onChange={(e) => setEnabled(e.target.checked)} 
              className="sr-only peer" 
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
          </label>
        </div>
      </div>

      <div className="flex justify-end pt-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-6 py-2.5 bg-primary text-white font-medium rounded-xl hover:bg-primary-hover shadow-lg shadow-primary/25 disabled:opacity-50 transition-all"
        >
          {saving ? 'Saving...' : <><Save className="w-4 h-4"/> Save Settings</>}
        </button>
      </div>
    </motion.div>
  );
}

export default AdminOverlapSettings;
