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
  const [newDept, setNewDept] = useState({ name: '', description: '' });

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
    if (!newDept.name.trim()) {
      showToast({ type: 'warning', message: 'Department name is required' });
      return;
    }
    try {
      setCreating(true);
      await api.post('/users/departments/', {
        name: newDept.name.trim(),
        description: newDept.description || '',
        affiliate_id: Number(id),
      });
      setNewDept({ name: '', description: '' });
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
          <div className="flex gap-2">
            <input
              type="text"
              value={newDept.name}
              onChange={(e) => setNewDept((p) => ({ ...p, name: e.target.value }))}
              placeholder="New department name"
              className="border px-3 py-2 rounded-md"
            />
            <input
              type="text"
              value={newDept.description}
              onChange={(e) => setNewDept((p) => ({ ...p, description: e.target.value }))}
              placeholder="Description (optional)"
              className="border px-3 py-2 rounded-md"
            />
            <button
              onClick={createDepartment}
              disabled={creating}
              className="px-3 py-2 bg-sky-600 text-white rounded-md hover:bg-sky-700 disabled:opacity-50"
            >
              {creating ? 'Creating...' : 'New Department'}
            </button>
          </div>
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
    </div>
  );
}
