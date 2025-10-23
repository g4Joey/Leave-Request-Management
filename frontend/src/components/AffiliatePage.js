import React, { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';

export default function AffiliatePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [affiliate, setAffiliate] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newDeptModal, setNewDeptModal] = useState({ open: false, name: '', description: '' });
  const [deleteModal, setDeleteModal] = useState({ open: false, selected: {}, processing: false });
  const [hodModal, setHodModal] = useState({ open: false, loading: false, department: null, selectedManagerId: '' });

  // Desired display order for departments (case-insensitive match)
  const desiredOrder = [
    'Finance&Accounts',
    'Government securities',
    'pensions&Provident',
    'private wealth & mutual fund',
    'Hr & admin',
    'Client Service/Marketing',
    'corporate finance',
    'IT',
    'Compliance',
    'Audit',
  ];

  const load = async () => {
    try {
      setLoading(true);
      const [affRes, deptRes] = await Promise.all([
        api.get(`/users/affiliates/${id}/`),
        api.get(`/users/departments/?affiliate_id=${id}`),
      ]);
      setAffiliate(affRes.data);
      const list = Array.isArray(deptRes.data?.results) ? deptRes.data.results : (deptRes.data || []);
      // Sort departments to follow desired order first, then others alphabetically
      const nameKey = (n) => (n || '').toString().trim().toLowerCase();
      const orderIndex = (n) => {
        const idx = desiredOrder.findIndex((x) => nameKey(x) === nameKey(n));
        return idx === -1 ? Number.POSITIVE_INFINITY : idx;
      };
      const sorted = [...list].sort((a, b) => {
        const oa = orderIndex(a.name);
        const ob = orderIndex(b.name);
        if (oa !== ob) return oa - ob;
        return nameKey(a.name).localeCompare(nameKey(b.name));
      });
      setDepartments(sorted);

      // Try to load staff scoped to this affiliate (for HOD dropdown and staff counts)
      try {
        const staffRes = await api.get(`/users/staff/?affiliate_id=${id}`);
        const payload = staffRes?.data;
        const depts = Array.isArray(payload)
          ? payload
          : (Array.isArray(payload?.results) ? payload.results : (Array.isArray(payload?.data) ? payload.data : []));
        const flattened = (depts || []).flatMap((d) =>
          (Array.isArray(d?.staff) ? d.staff : []).map((s) => ({
            id: s.id,
            name: s.name,
            email: s.email,
            department: d.name,
            employee_id: s.employee_id,
            role: s.role,
            manager: s.manager,
            hire_date: s.hire_date,
          }))
        );
        setEmployees(flattened);
      } catch (e) {
        // Fallback: load all staff and filter by departments we have (best-effort)
        try {
          const staffResAll = await api.get(`/users/staff/`);
          const payload = staffResAll?.data;
          const depts = Array.isArray(payload)
            ? payload
            : (Array.isArray(payload?.results) ? payload.results : (Array.isArray(payload?.data) ? payload.data : []));
          const deptNames = new Set(sorted.map((d) => (d?.name || '').toString()));
          const flattened = (depts || []).flatMap((d) =>
            (Array.isArray(d?.staff) ? d.staff : []).map((s) => ({
              id: s.id,
              name: s.name,
              email: s.email,
              department: d.name,
              employee_id: s.employee_id,
              role: s.role,
              manager: s.manager,
              hire_date: s.hire_date,
            }))
          ).filter((s) => deptNames.has(s.department));
          setEmployees(flattened);
        } catch (_) {
          setEmployees([]);
        }
      }
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

  const openHodModal = (department) => {
    setHodModal({ open: true, loading: false, department, selectedManagerId: '' });
  };

  const updateDepartmentHod = async () => {
    setHodModal((prev) => ({ ...prev, loading: true }));
    try {
      await api.post(`/users/departments/${hodModal.department.id}/set_manager/`, {
        manager_id: hodModal.selectedManagerId || null,
      });
      showToast({ type: 'success', message: `Department HOD ${hodModal.selectedManagerId ? 'updated' : 'removed'} successfully!` });
      setHodModal({ open: false, loading: false, department: null, selectedManagerId: '' });
      await load();
    } catch (error) {
      console.error('Error updating HOD:', error);
      showToast({ type: 'error', message: error.response?.data?.error || 'Failed to update department HOD' });
      setHodModal((prev) => ({ ...prev, loading: false }));
    }
  };

  const staffCountByDept = useMemo(() => {
    const counts = {};
    employees.forEach((e) => {
      counts[e.department] = (counts[e.department] || 0) + 1;
    });
    return counts;
  }, [employees]);

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
          <div className="flex items-center gap-2">
            <button
              onClick={() => setNewDeptModal({ open: true, name: '', description: '' })}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium border border-gray-200"
            >
              New department
            </button>
            <button
              onClick={() => setDeleteModal({ open: true, selected: {}, processing: false })}
              disabled={departments.length === 0}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium border border-red-600 text-red-600 disabled:opacity-50"
              title={departments.length === 0 ? 'No departments to delete' : 'Delete departments'}
            >
              Delete departments
            </button>
          </div>
        </div>
      </div>

      <div className="bg-white shadow rounded-md p-4">
        <h2 className="text-lg font-medium mb-4">Departments</h2>
        {departments.length === 0 ? (
          <div className="text-sm text-gray-500">No departments under this affiliate yet.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {departments.map((d) => (
              <div key={d.id} className="border border-gray-200 rounded-lg overflow-hidden bg-white">
                <div className="w-full px-4 py-4 text-left">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-lg font-medium text-gray-900">{d.name}</h4>
                      {d.description && (
                        <p className="text-sm text-gray-500 mt-1">{d.description}</p>
                      )}
                      <p className="text-sm text-gray-600 mt-1">
                        {(typeof d.staff_count === 'number' ? d.staff_count : (staffCountByDept[d.name] || 0))} staff member{(typeof d.staff_count === 'number' ? d.staff_count : (staffCountByDept[d.name] || 0)) !== 1 ? 's' : ''}
                      </p>
                      {d.manager ? (
                        <p className="text-sm text-blue-600 mt-1">
                          <span className="font-medium">HOD:</span> {d.manager.name} ({d.manager.employee_id})
                        </p>
                      ) : (
                        <p className="text-sm text-amber-600 mt-1">
                          <span className="font-medium">⚠️ No HOD assigned</span>
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => openHodModal(d)}
                        className="px-3 py-1 text-xs font-medium rounded-md border border-blue-200 text-blue-700 hover:bg-blue-50"
                      >
                        Set HOD
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
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

      {deleteModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
          <div className="bg-white rounded-md shadow p-6 w-full max-w-lg">
            <h3 className="text-lg font-semibold mb-4">Delete Departments</h3>
            {departments.length === 0 ? (
              <div className="text-sm text-gray-500">There are no departments to delete.</div>
            ) : (
              <>
                <div className="flex items-center justify-between mb-3">
                  <button
                    className="text-sm text-sky-600 hover:underline"
                    onClick={() => {
                      const all = {};
                      departments.forEach(d => { all[d.id] = true; });
                      setDeleteModal(prev => ({ ...prev, selected: all }));
                    }}
                  >
                    Select all
                  </button>
                  <div className="text-sm text-gray-600">
                    Selected: {Object.values(deleteModal.selected).filter(Boolean).length}
                  </div>
                </div>
                <div className="max-h-64 overflow-y-auto border rounded">
                  {departments.map((d) => (
                    <label key={d.id} className="flex items-start gap-3 p-3 border-b last:border-b-0">
                      <input
                        type="checkbox"
                        className="mt-1"
                        checked={!!deleteModal.selected[d.id]}
                        onChange={(e) => {
                          const checked = e.target.checked;
                          setDeleteModal(prev => ({
                            ...prev,
                            selected: { ...prev.selected, [d.id]: checked },
                          }));
                        }}
                      />
                      <div>
                        <div className="font-medium text-gray-900">{d.name}</div>
                        {d.description && <div className="text-sm text-gray-600">{d.description}</div>}
                      </div>
                    </label>
                  ))}
                </div>
              </>
            )}
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setDeleteModal({ open: false, selected: {}, processing: false })}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                disabled={deleteModal.processing}
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  const ids = Object.keys(deleteModal.selected).filter((k) => deleteModal.selected[k]).map(Number);
                  if (ids.length === 0) {
                    showToast({ type: 'warning', message: 'Select at least one department to delete' });
                    return;
                  }
                  try {
                    setDeleteModal(prev => ({ ...prev, processing: true }));
                    const results = await Promise.allSettled(ids.map((deptId) => api.delete(`/users/departments/${deptId}/`)));
                    const failed = results.filter(r => r.status === 'rejected');
                    if (failed.length > 0) {
                      showToast({ type: 'warning', message: `Deleted ${ids.length - failed.length} of ${ids.length} departments (some failed)` });
                    } else {
                      showToast({ type: 'success', message: `Deleted ${ids.length} department${ids.length === 1 ? '' : 's'}` });
                    }
                    await load();
                    setDeleteModal({ open: false, selected: {}, processing: false });
                  } catch (e) {
                    const msg = e.response?.data?.detail || 'Failed to delete departments';
                    showToast({ type: 'error', message: msg });
                    setDeleteModal(prev => ({ ...prev, processing: false }));
                  }
                }}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-red-600 text-white bg-red-600 hover:bg-red-700"
                disabled={deleteModal.processing || Object.values(deleteModal.selected).every(v => !v)}
              >
                {deleteModal.processing ? 'Deleting...' : 'Delete selected'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* HOD Management Modal */}
      {hodModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
          <div className="bg-white rounded-md shadow p-6 w-full max-w-lg">
            <h3 className="text-lg font-semibold mb-2">Set HOD for {hodModal.department?.name}</h3>
            <p className="text-sm text-gray-600 mb-4">Select a manager to serve as Head of Department (HOD) for approval of leave requests.</p>
            {hodModal.loading ? (
              <div className="text-sm text-gray-500">Updating...</div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Select Manager/HOD</label>
                  <select
                    className="w-full border rounded-md px-3 py-2"
                    value={hodModal.selectedManagerId}
                    onChange={(e) => setHodModal((prev) => ({ ...prev, selectedManagerId: e.target.value }))}
                  >
                    <option value="">-- No HOD (Remove current) --</option>
                    {employees
                      .filter((emp) => emp.department === hodModal.department?.name)
                      .map((emp) => (
                        <option key={emp.id} value={emp.id}>
                          {emp.name} ({emp.employee_id})
                        </option>
                      ))}
                  </select>
                </div>
                {hodModal.department?.manager && (
                  <div className="text-sm text-gray-600">
                    <span className="font-medium">Current HOD:</span> {hodModal.department.manager.name} ({hodModal.department.manager.employee_id})
                  </div>
                )}
              </div>
            )}
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setHodModal({ open: false, loading: false, department: null, selectedManagerId: '' })}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                disabled={hodModal.loading}
              >
                Cancel
              </button>
              <button
                onClick={updateDepartmentHod}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-blue-600 text-white bg-blue-600 hover:bg-blue-700"
                disabled={hodModal.loading}
              >
                {hodModal.loading ? 'Updating...' : 'Update HOD'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
