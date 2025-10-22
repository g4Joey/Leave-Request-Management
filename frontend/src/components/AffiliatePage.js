import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';

export default function AffiliatePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [affiliate, setAffiliate] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newDeptModal, setNewDeptModal] = useState({ open: false, name: '', description: '' });

  const load = async () => {
    try {
      setLoading(true);
      const [affRes, deptRes] = await Promise.all([
        api.get(`/users/affiliates/${id}/`),
        api.get(`/users/departments/?affiliate_id=${id}`),
      ]);
      setAffiliate(affRes.data);
      const list = Array.isArray(deptRes.data?.results) ? deptRes.data.results : (deptRes.data || []);
      setDepartments(list);
    } catch (e) {
      const msg = e.response?.data?.detail || e.response?.data?.error || 'Failed to load affiliate';
      showToast({ type: 'error', message: msg });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const createDepartment = async () => {
    if (!newDeptModal.name.trim()) {
      showToast({ type: 'warning', message: 'Department name is required' });
      return;
    }
    try {
      setCreating(true);
      await api.post('/users/departments/', {
        name: newDeptModal.name.trim(),
        description: newDeptModal.description || '',
        affiliate_id: Number(id),
      });
      setNewDeptModal({ open: false, name: '', description: '' });
      await load();
      showToast({ type: 'success', message: 'Department created' });
    } catch (e) {
      const msg = e.response?.data?.detail || e.response?.data?.name?.join?.(', ') || e.response?.data?.error || 'Failed to create department';
      showToast({ type: 'error', message: msg });
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-2 border-sky-500 border-t-transparent"></div>
      </div>
    );
  }

  if (!affiliate) {
    return (
      <div className="text-center text-gray-600">
        Affiliate not found.
        <div>
          <button onClick={() => navigate('/staff')} className="mt-3 text-sky-600 hover:underline">Back to Staff</button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <button onClick={() => navigate('/staff')} className="text-sm text-gray-600 hover:underline">← Back</button>
          <h1 className="text-2xl font-semibold mt-1">{affiliate.name}</h1>
        </div>
        <div>
          <button
            onClick={() => setNewDeptModal({ open: true, name: '', description: '' })}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium border border-gray-200"
          >
            New department
          </button>
        </div>
      </div>

      <div className="bg-white shadow rounded-md p-4">
        <h2 className="text-lg font-medium mb-4">Departments</h2>
        {departments.length === 0 ? (
          <div className="text-sm text-gray-500">No departments under this affiliate yet.</div>
        ) : (
          <ul className="divide-y">
            {departments.map((d) => (
              <li key={d.id} className="py-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-gray-900">{d.name}</div>
                    {d.description && (
                      <div className="text-sm text-gray-600">{d.description}</div>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {newDeptModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
          <div className="bg-white rounded-md shadow p-6 w-full max-w-sm">
            <h3 className="text-lg font-semibold mb-4">Create New Department</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Department Name *</label>
                <input
                  type="text"
                  value={newDeptModal.name}
                  onChange={(e) => setNewDeptModal((prev) => ({ ...prev, name: e.target.value }))}
                  className="w-full border rounded-md px-3 py-2"
                  placeholder="e.g. Engineering"
                  disabled={creating}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={newDeptModal.description}
                  onChange={(e) => setNewDeptModal((prev) => ({ ...prev, description: e.target.value }))}
                  className="w-full border rounded-md px-3 py-2"
                  rows="3"
                  placeholder="Optional description"
                  disabled={creating}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setNewDeptModal({ open: false, name: '', description: '' })}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                disabled={creating}
              >
                Cancel
              </button>
              <button
                onClick={createDepartment}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-blue-600 text-white bg-blue-600 hover:bg-blue-700"
                disabled={creating}
              >
                {creating ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
