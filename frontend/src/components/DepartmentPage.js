import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { useAuth } from '../contexts/AuthContext';

function toCSV(rows, headers) {
  const esc = (v = '') => `"${String(v).replace(/"/g, '""')}"`;
  const headerLine = headers.map(esc).join(',');
  const lines = rows.map((r) => headers.map((h) => esc(r[h])).join(','));
  return [headerLine, ...lines].join('\n');
}

export default function DepartmentPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [department, setDepartment] = useState(null);
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [profileModal, setProfileModal] = useState({ open: false, loading: false, employee: null, data: null, error: null });
  const [benefitsModal, setBenefitsModal] = useState({ open: false, loading: false, employee: null, rows: [] });
  const [leaveHistoryModal, setLeaveHistoryModal] = useState({ open: false, loading: false, employee: null, requests: [], searchQuery: '' });
  const [profileEditFields, setProfileEditFields] = useState({ employee_id: '', hire_date: '', new_email: '', new_password: '' });
  const [profileFieldsSaving, setProfileFieldsSaving] = useState(false);
  const [profileRoleSaving, setProfileRoleSaving] = useState(false);
  const [resetPasswordSaving, setResetPasswordSaving] = useState(false);
  const [updateEmailSaving, setUpdateEmailSaving] = useState(false);
  const [selectedRole, setSelectedRole] = useState('');
  const [departmentsList, setDepartmentsList] = useState([]);
  const { user } = useAuth();
  const departments = departmentsList;
  const handleRoleChange = (newRole) => setSelectedRole(newRole);

  const filteredLeaveHistory = useMemo(() => {
    const qRaw = (leaveHistoryModal.searchQuery || '').trim();
    const query = qRaw.toLowerCase();
    const requests = leaveHistoryModal.requests || [];

    const toISODate = (val) => {
      if (!val) return null;
      const s = String(val).split('T')[0];
      if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
      const dt = new Date(val);
      if (!isNaN(dt)) {
        const y = dt.getFullYear(); const m = String(dt.getMonth() + 1).padStart(2, '0'); const d = String(dt.getDate()).padStart(2, '0');
        return `${y}-${m}-${d}`;
      }
      return null;
    };

    const toUSDate = (val) => {
      const iso = toISODate(val);
      if (!iso) return null;
      const [y, m, d] = iso.split('-');
      return `${m}/${d}/${y}`;
    };

    // If no query, show only the last 5 requests (most recent first assumed already)
    if (!query) return requests.slice(0, 5);

    // Try to detect if the query is a date (mm/dd/yyyy or yyyy-mm-dd)
    let parsedQueryDate = null;
    if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(qRaw)) {
      const [mm, dd, yyyy] = qRaw.split('/').map((t) => t.padStart(2, '0'));
      parsedQueryDate = `${yyyy}-${mm}-${dd}`;
    } else if (/^\d{4}-\d{2}-\d{2}$/.test(qRaw)) {
      parsedQueryDate = qRaw;
    }

    return requests.filter((request) => {
      const type = String(request.leave_type_name || request.leave_type?.name || '').toLowerCase();
      const reason = String(request.reason || '').toLowerCase();
      const status = String(request.status || '').toLowerCase();
      const comments = String(request.approval_comments || '').toLowerCase();

      if (type.includes(query) || reason.includes(query) || status.includes(query) || comments.includes(query)) return true;

      // date string matching against start/end/created dates in either ISO or US format
      const startISO = toISODate(request.start_date);
      const endISO = toISODate(request.end_date);
      const createdISO = toISODate(request.created_at);
      const startUS = toUSDate(request.start_date);
      const endUS = toUSDate(request.end_date);
      const createdUS = toUSDate(request.created_at);

      if (parsedQueryDate) {
        if (parsedQueryDate === startISO || parsedQueryDate === endISO || parsedQueryDate === createdISO) return true;
      }

      if (startISO && startISO.includes(query)) return true;
      if (endISO && endISO.includes(query)) return true;
      if (createdISO && createdISO.includes(query)) return true;
      if (startUS && startUS.toLowerCase().includes(query)) return true;
      if (endUS && endUS.toLowerCase().includes(query)) return true;
      if (createdUS && createdUS.toLowerCase().includes(query)) return true;

      return false;
    });
  }, [leaveHistoryModal.requests, leaveHistoryModal.searchQuery]);

  const load = async () => {
    try {
      setLoading(true);
      const [deptRes, staffRes] = await Promise.all([
        api.get(`/users/departments/${id}/`),
        api.get(`/users/staff/?department_id=${id}`),
      ]);
      setDepartment(deptRes.data);

      // normalize staff results (results or array)
      let base = Array.isArray(staffRes.data?.results) ? staffRes.data.results : (Array.isArray(staffRes.data) ? staffRes.data : []);

      // If the response is a single object with a `staff` array (or the API
      // returned department objects with `staff` arrays), extract the staff
      // list from the matching department entry.
      if (!base.length) {
        // sometimes the endpoint returns an object with `staff` directly
        if (staffRes.data && Array.isArray(staffRes.data.staff)) {
          base = staffRes.data.staff;
        }
      } else {
        const anyHaveStaffArray = base.some((it) => Array.isArray(it?.staff));
        if (anyHaveStaffArray) {
          // try to find the department entry that matches our department id or name
          const match = base.find((it) => {
            if (!it) return false;
            if (it.id && deptRes.data?.id && Number(it.id) === Number(deptRes.data.id)) return true;
            if (it.name && deptRes.data?.name && String(it.name).trim() === String(deptRes.data.name).trim()) return true;
            return false;
          }) || base[0];
          if (match && Array.isArray(match.staff)) {
            base = match.staff;
          } else {
            // fall back to fetching all staff and filtering below
            base = [];
          }
        }
      }

      // If we still don't have staff, fallback to fetching all staff and filtering
      if (!base.length) {
        try {
          const allRes = await api.get('/users/staff/');
          const all = Array.isArray(allRes.data?.results) ? allRes.data.results : (Array.isArray(allRes.data) ? allRes.data : []);
          const deptIdNum = Number(id);
          const deptName = deptRes.data?.name;
          base = all.filter((s) => {
            if (s.department_id && deptIdNum && Number(s.department_id) === deptIdNum) return true;
            if (s.department && typeof s.department === 'object' && s.department.id && Number(s.department.id) === deptIdNum) return true;
            if (s.department_name && deptName && String(s.department_name) === String(deptName)) return true;
            if (s.department && typeof s.department === 'string' && deptName && String(s.department) === String(deptName)) return true;
            return false;
          });
        } catch (err) {
          console.warn('Fallback staff fetch failed, using original response', err);
        }
      }

      setStaff(base.map((s) => ({
        id: s.id,
        name: s.name || `${s.first_name || ''} ${s.last_name || ''}`.trim() || s.email,
        email: s.email,
        role: s.role,
        employee_id: s.employee_id,
      })));
    } catch (e) {
      console.error('Failed to load department', e);
      showToast({ type: 'error', message: 'Failed to load department' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [id]);

  // --- Modal handlers reused from StaffManagement (simplified local versions) ---
  const openProfile = async (emp) => {
    if (!emp || !emp.id) return;
    setProfileModal({ open: true, loading: true, employee: emp, data: null, error: null });
    try {
      const res = await api.get(`/users/${emp.id}/`);
      const d = res.data || {};
      const normalized = {
        id: d.id,
        employee_id: d.employee_id,
        email: d.email,
        role: (d.role === 'employee' || d.role === 'staff') ? 'junior_staff' : d.role,
        department_name: d.department?.name || d.department_name || (typeof d.department === 'string' ? d.department : null),
        department_id: d.department?.id || d.department_id || null,
        hire_date: d.hire_date,
        first_name: d.first_name,
        last_name: d.last_name,
      };
      setProfileModal({ open: true, loading: false, employee: emp, data: normalized, error: null });
      // Initialize edit fields
      setProfileEditFields({ employee_id: normalized.employee_id || '', hire_date: normalized.hire_date || '', new_email: '', new_password: '', department_id: normalized.department_id || '' });
      setSelectedRole(normalized.role || 'junior_staff');
    } catch (e) {
      console.error('Failed to load profile', e);
      setProfileModal({ open: true, loading: false, employee: emp, data: null, error: 'Failed to load profile' });
      showToast({ type: 'error', message: 'Failed to load profile' });
    }
  };

  const openBenefits = async (emp) => {
    if (!emp || !emp.id) return;
    setBenefitsModal({ open: true, loading: true, employee: emp, rows: [] });
    try {
      const res = await api.get(`/leaves/balances/employee/${emp.id}/current_year/`);
      const items = res.data?.items || [];
      const rows = items.map((it) => ({ leave_type: it.leave_type.id, leave_type_name: it.leave_type.name, entitled_days: String(it.entitled_days ?? 0) }));
      setBenefitsModal({ open: true, loading: false, employee: emp, rows });
    } catch (e) {
      console.error('Failed to load benefits', e);
      setBenefitsModal({ open: false, loading: false, employee: null, rows: [] });
      showToast({ type: 'error', message: 'Failed to load benefits' });
    }
  };

  const saveBenefits = async () => {
    const { employee, rows } = benefitsModal;
    const payload = { items: rows.map((r) => ({ leave_type: r.leave_type, entitled_days: parseInt(r.entitled_days, 10) || 0 })) };
    try {
      setBenefitsModal((prev) => ({ ...prev, loading: true }));
      const res = await api.post(`/leaves/balances/employee/${employee.id}/set_entitlements/`, payload);
      const errs = res.data?.errors || [];
      if (errs.length) showToast({ type: 'warning', message: `Saved with ${errs.length} warnings` });
      else showToast({ type: 'success', message: 'Benefits saved' });
      setBenefitsModal({ open: false, loading: false, employee: null, rows: [] });
    } catch (e) {
      console.error('Failed to save benefits', e);
      setBenefitsModal((prev) => ({ ...prev, loading: false }));
      showToast({ type: 'error', message: 'Failed to save benefits' });
    }
  };

  const saveProfileFields = async () => {
    if (!profileModal?.employee?.id) return;
    const currentData = profileModal.data || {};
    const updates = {};
    if (profileEditFields.employee_id !== (currentData.employee_id || '')) {
      const trimmedEmployeeId = profileEditFields.employee_id.trim();
      if (!trimmedEmployeeId) {
        showToast({ type: 'error', message: 'Employee ID is required' });
        return;
      }
      updates.employee_id = trimmedEmployeeId;
    }
    if (profileEditFields.hire_date !== (currentData.hire_date || '')) {
      updates.hire_date = profileEditFields.hire_date;
    }
    // Check if department changed (HR/Admin only)
    if ((user?.role === 'hr' || user?.role === 'admin' || user?.is_superuser)) {
      const currentDept = currentData.department_id || null;
      const newDept = profileEditFields.department_id || null;
      if ((String(newDept) !== String(currentDept))) {
        updates.department_id = newDept || null;
      }
    }

    if (Object.keys(updates).length === 0) return;
    try {
      setProfileFieldsSaving(true);
      const res = await api.patch(`/users/${profileModal.employee.id}/`, updates);
      const updatedUser = res.data || {};
      showToast({ type: 'success', message: 'Profile updated successfully' });
      // update modal data
      setProfileModal(prev => ({ ...prev, data: prev.data ? { ...prev.data, employee_id: updatedUser.employee_id, hire_date: updatedUser.hire_date } : prev.data }));
      setProfileEditFields(prev => ({ ...prev, employee_id: updatedUser.employee_id || '', hire_date: updatedUser.hire_date || '' }));
      // refresh department list
      await load();
    } catch (e) {
      console.error('Profile update error:', e.response?.data || e);
      const msg = e.response?.data?.detail || e.response?.data?.error || 'Failed to update profile';
      showToast({ type: 'error', message: msg });
    } finally {
      setProfileFieldsSaving(false);
    }
  };

  const resetEmployeePassword = async () => {
    if (!profileModal?.employee?.id) return;
    const newPassword = profileEditFields.new_password?.trim() || '';
    if (!newPassword) { showToast({ type: 'error', message: 'New password is required' }); return; }
    if (newPassword.length < 8) { showToast({ type: 'error', message: 'Password must be at least 8 characters' }); return; }
    try {
      setResetPasswordSaving(true);
      await api.post(`/users/${profileModal.employee.id}/reset-password/`, { new_password: newPassword });
      showToast({ type: 'success', message: 'Password reset successfully' });
      setProfileEditFields(prev => ({ ...prev, new_password: '' }));
    } catch (e) {
      console.error('Password reset error:', e.response?.data || e);
      const msg = e.response?.data?.error || e.response?.data?.detail || 'Failed to reset password';
      showToast({ type: 'error', message: msg });
    } finally {
      setResetPasswordSaving(false);
    }
  };

  const updateEmployeeEmail = async () => {
    if (!profileModal?.employee?.id) return;
    const newEmail = (profileEditFields.new_email || '').trim();
    if (!newEmail) { showToast({ type: 'error', message: 'New email is required' }); return; }
    if (!newEmail.includes('@')) { showToast({ type: 'error', message: 'Invalid email format' }); return; }
    try {
      setUpdateEmailSaving(true);
      const res = await api.patch(`/users/${profileModal.employee.id}/update-email/`, { email: newEmail });
      showToast({ type: 'success', message: 'Email updated successfully' });
      setProfileModal(prev => ({ ...prev, data: prev.data ? { ...prev.data, email: res.data.new_email } : prev.data }));
      setProfileEditFields(prev => ({ ...prev, new_email: '' }));
      await load();
    } catch (e) {
      console.error('Email update error:', e.response?.data || e);
      const msg = e.response?.data?.error || e.response?.data?.detail || 'Failed to update email';
      showToast({ type: 'error', message: msg });
    } finally {
      setUpdateEmailSaving(false);
    }
  };

  const saveProfileRole = async () => {
    if (!profileModal?.employee?.id || !selectedRole) return;
    try {
      setProfileRoleSaving(true);
      const res = await api.patch(`/users/${profileModal.employee.id}/`, { role: selectedRole });
      showToast({ type: 'success', message: 'Role updated' });
      setProfileModal(prev => ({ ...prev, data: prev.data ? { ...prev.data, role: res.data.role } : prev.data }));
      await load();
    } catch (e) {
      console.error('Failed to update role', e.response?.data || e);
      showToast({ type: 'error', message: e.response?.data?.detail || 'Failed to update role' });
    } finally {
      setProfileRoleSaving(false);
    }
  };

  const openLeaveHistory = async (emp) => {
    if (!emp || !emp.id) return;
    setLeaveHistoryModal({ open: true, loading: true, employee: emp, requests: [], searchQuery: '' });
    try {
      const res = await api.get(`/leaves/manager/?employee=${emp.id}&ordering=-created_at`);
      const requests = res.data?.results || res.data || [];
      setLeaveHistoryModal({ open: true, loading: false, employee: emp, requests, searchQuery: '' });
    } catch (e) {
      console.error('Failed to load leave history', e);
      setLeaveHistoryModal({ open: true, loading: false, employee: emp, requests: [], searchQuery: '' });
      showToast({ type: 'error', message: 'Failed to load leave history' });
    }
  };

  const handleExportLeaveHistoryCSV = () => {
    const requests = leaveHistoryModal.requests;
    if (!requests || requests.length === 0) {
      showToast({ type: 'info', message: 'No leave history to export.' });
      return;
    }

    const formatDate = (val) => {
      if (!val) return '';
      const s = String(val);
      if (/^\d{4}-\d{2}-\d{2}/.test(s)) {
        const [y, m, d] = s.split('T')[0].split('-');
        return `${d}-${m}-${y}`;
      }
      const dt = new Date(s);
      if (!isNaN(dt)) {
        const dd = String(dt.getDate()).padStart(2, '0');
        const mm = String(dt.getMonth() + 1).padStart(2, '0');
        const yy = dt.getFullYear();
        return `${dd}-${mm}-${yy}`;
      }
      return s;
    };

    const usFormat = (val) => {
      if (!val) return '';
      const s = String(val).trim();
      const base = s.split('T')[0];
      if (/^\d{4}-\d{2}-\d{2}$/.test(base)) {
        const [y, m, d] = base.split('-');
        return `${m}/${d}/${y}`;
      }
      const dt = new Date(s);
      if (!isNaN(dt)) {
        const mm = String(dt.getMonth() + 1).padStart(2, '0');
        const dd = String(dt.getDate()).padStart(2, '0');
        const yy = dt.getFullYear();
        return `${mm}/${dd}/${yy}`;
      }
      return s;
    };

    const total = requests.length;
    const approved = requests.filter(r => r.status === 'approved').length;
    const rejected = requests.filter(r => r.status === 'rejected').length;
    const pending = requests.filter(r => ['pending', 'manager_approved', 'hr_approved'].includes(r.status)).length;

    const csvRows = [
      ['Total', 'Approved', 'Rejected', 'Pending'],
      [total, approved, rejected, pending],
      [],
      ['Leave Type', 'Start Date', 'End Date', 'Days', 'Status', 'Reason', 'Comments', 'Requested At', 'Manager Approval Date', 'HR Approval Date', 'CEO Approval Date', 'Final Approval/Rejection Date']
    ];

    requests.forEach(request => {
      csvRows.push([
        request.leave_type_name || request.leave_type?.name || 'Unknown Leave Type',
        usFormat(request.start_date),
        usFormat(request.end_date),
        request.total_days,
        request.status,
        request.reason || '',
        request.approval_comments || '',
        usFormat(request.created_at),
        usFormat(request.manager_approval_date),
        usFormat(request.hr_approval_date),
        usFormat(request.ceo_approval_date),
        usFormat(request.approval_date)
      ]);
    });

    const csvContent = csvRows.map(e => e.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.setAttribute('download', `leave_history_${leaveHistoryModal.employee?.name?.replace(/\s+/g, '_') || 'employee'}.csv`);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast({ type: 'success', message: 'Leave history exported.' });
  };

  useEffect(() => {
    const loadDepts = async () => {
      try {
        const res = await api.get('/users/departments/');
        const list = Array.isArray(res.data?.results) ? res.data.results : (Array.isArray(res.data) ? res.data : []);
        setDepartmentsList(list);
      } catch (e) {
        setDepartmentsList([]);
      }
    };
    loadDepts();
  }, []);

  const handleExportStaffCSV = () => {
    const headers = ['name', 'email', 'employee_id', 'role'];
    const csv = toCSV(staff, headers);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(department?.name || 'department').replace(/[^a-z0-9\-]/gi, '_')}_staff.csv`;
    a.click();
    URL.revokeObjectURL(url);
    showToast({ type: 'success', message: 'Exported department staff CSV' });
  };

  const handleExportLeaveRequestsCSV = async () => {
    try {
      showToast({ type: 'info', message: 'Fetching leave requests...' });
      // attempt to fetch leave requests for this department by employee_department_id
      const res = await api.get(`/leaves/requests/?employee_department_id=${id}&limit=1000`);
      const base = Array.isArray(res.data?.results) ? res.data.results : (Array.isArray(res.data) ? res.data : []);
      if (!base.length) {
        showToast({ type: 'info', message: 'No leave requests found for this department' });
        return;
      }
      const headers = ['id', 'employee_name', 'employee_email', 'start_date', 'end_date', 'status', 'status_display'];
      const rows = base.map((r) => ({
        id: r.id,
        employee_name: r.employee_name || r.name || '',
        employee_email: r.employee_email || r.email || '',
        start_date: r.start_date || '',
        end_date: r.end_date || '',
        status: r.status || '',
        status_display: r.status_display || r.get_dynamic_status_display || '',
      }));
      const csv = toCSV(rows, headers);
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(department?.name || 'department').replace(/[^a-z0-9\-]/gi, '_')}_leave_requests.csv`;
      a.click();
      URL.revokeObjectURL(url);
      showToast({ type: 'success', message: 'Exported department leave requests' });
    } catch (e) {
      console.error('Failed to export leave requests', e);
      showToast({ type: 'error', message: 'Failed to export leave requests' });
    }
  };

  if (loading) return (
    <div className="flex justify-center items-center h-48">
      <div className="animate-spin rounded-full h-10 w-10 border-2 border-sky-500 border-t-transparent"></div>
    </div>
  );

  if (!department) return (
    <div className="text-center text-gray-600">Department not found</div>
  );

  return (
    <>
    <div className="max-w-4xl mx-auto bg-white shadow rounded p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <button onClick={() => {
            if (department?.affiliate?.id) {
              navigate(`/staff/affiliates/${department.affiliate.id}`);
            } else {
              navigate('/staff');
            }
          }} className="text-sm text-gray-600 hover:underline">← Back to Departments</button>
          <h2 className="text-2xl font-semibold mt-1">{department.name}</h2>
          {department.description && <p className="text-sm text-gray-600 mt-1">{department.description}</p>}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => load()} className="px-3 py-2 rounded-md border text-sm">Refresh</button>
          <button onClick={handleExportStaffCSV} className="px-3 py-2 rounded-md border text-sm">Export Staff</button>
          <button onClick={handleExportLeaveRequestsCSV} className="px-3 py-2 rounded-md bg-blue-600 text-white text-sm">Export Leave Requests</button>
        </div>
      </div>
      
          {/* Profile Modal (local) */}
          {profileModal.open && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
              <div className="bg-white rounded-md shadow p-6 w-full max-w-lg">
                <h3 className="text-lg font-semibold mb-2">Profile: {profileModal.employee?.name}</h3>
                {profileModal.loading && (
                  <div className="text-sm text-gray-500">Loading...</div>
                )}
                {!profileModal.loading && profileModal.error && (
                  <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-3 mb-2">
                    {profileModal.error}
                  </div>
                )}
                {!profileModal.loading && !profileModal.error && profileModal.data && (
                  <div className="space-y-4 text-sm">
                    {(() => { console.log('[DepartmentPage] Rendering profile modal with data:', profileModal.data); return null; })()}
                    
                    {/* Employee ID - Editable */}
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Employee ID</label>
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          value={profileEditFields.employee_id}
                          onChange={(e) => setProfileEditFields(prev => ({ ...prev, employee_id: e.target.value }))}
                          className="border rounded-md px-2 py-1 text-sm flex-1"
                          placeholder="Enter employee ID"
                        />
                      </div>
                    </div>

                    {/* Email - Editable by Admin/HR */}
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Email</label>
                      <div className="space-y-2">
                        <div className="text-sm"><span className="font-medium">Current:</span> {profileModal.data.email || '—'}</div>
                        {(user?.role === 'hr' || user?.role === 'admin' || user?.is_superuser) && (
                          <div className="flex items-center gap-2">
                            <input
                              type="email"
                              value={profileEditFields.new_email}
                              onChange={(e) => setProfileEditFields(prev => ({ ...prev, new_email: e.target.value }))}
                              className="border rounded-md px-2 py-1 text-sm flex-1"
                              placeholder="Enter new email"
                            />
                            <button
                              onClick={updateEmployeeEmail}
                              disabled={updateEmailSaving || !profileEditFields.new_email}
                              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border border-blue-600 text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                            >
                              {updateEmailSaving ? 'Updating...' : 'Update Email'}
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                    
                    {/* Department - editable for HR/Admin, read-only otherwise */}
                    {((user?.role === 'hr' || user?.role === 'admin' || user?.is_superuser)) ? (
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Department</label>
                        <select
                          value={profileEditFields.department_id || ''}
                          onChange={(e) => setProfileEditFields(prev => ({ ...prev, department_id: e.target.value }))}
                          className="w-full border rounded-md px-2 py-1 text-sm"
                        >
                          <option value="">-- No department --</option>
                          {departments.map((d) => (
                            <option key={d.id} value={d.id}>{d.name}</option>
                          ))}
                        </select>
                      </div>
                    ) : (
                      <div><span className="font-medium">Department:</span> {(profileModal.data.role === 'ceo' || /^executive(s)?$/i.test(profileModal.data.department_name || '')) ? '—' : (profileModal.data.department_name || '—')}</div>
                    )}

                    {/* Hire Date - Editable */}
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Hire Date</label>
                      <div className="flex items-center gap-2">
                        <input
                          type="date"
                          value={profileEditFields.hire_date}
                          onChange={(e) => setProfileEditFields(prev => ({ ...prev, hire_date: e.target.value }))}
                          className="border rounded-md px-2 py-1 text-sm flex-1"
                        />
                      </div>
                    </div>

                    {/* Save Profile Fields Button */}
                    {(profileEditFields.employee_id !== (profileModal.data.employee_id || '') || 
                      profileEditFields.hire_date !== (profileModal.data.hire_date || '')) && (
                      <div className="flex justify-end">
                        <button
                          onClick={saveProfileFields}
                          disabled={profileFieldsSaving}
                          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border border-green-600 text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
                        >
                          {profileFieldsSaving ? 'Saving...' : 'Save Profile Changes'}
                        </button>
                      </div>
                    )}

                    {/* Role Management */}
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Role</label>
                      <div className="flex items-center gap-2">
                        <select
                          value={selectedRole || profileModal.data.role || 'junior_staff'}
                          onChange={(e) => handleRoleChange(e.target.value)}
                          className="border rounded-md px-2 py-1 text-sm"
                          disabled={profileRoleSaving}
                        >
                          <option value="junior_staff">Junior Staff</option>
                          <option value="senior_staff">Senior Staff</option>
                          <option value="manager">Head of Department</option>
                          <option value="hr">HR</option>
                          <option value="ceo">CEO</option>
                          <option value="admin">Admin</option>
                        </select>
                        <button
                          onClick={saveProfileRole}
                          disabled={profileRoleSaving || (profileModal.data.role || 'junior_staff') === selectedRole}
                          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border border-sky-600 text-white bg-sky-600 disabled:opacity-50"
                        >
                          {profileRoleSaving ? 'Saving...' : 'Save Role'}
                        </button>
                      </div>
                    </div>

                    {/* Password Reset - Admin/HR Only */}
                    {(user?.role === 'hr' || user?.role === 'admin' || user?.is_superuser) && (
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Reset Password</label>
                        <div className="flex items-center gap-2">
                          <input
                            type="password"
                            value={profileEditFields.new_password}
                            onChange={(e) => setProfileEditFields(prev => ({ ...prev, new_password: e.target.value }))}
                            className="border rounded-md px-2 py-1 text-sm flex-1"
                            placeholder="Enter new password (min 8 chars)"
                          />
                          <button
                            onClick={resetEmployeePassword}
                            disabled={resetPasswordSaving || !profileEditFields.new_password}
                            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border border-red-600 text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
                          >
                            {resetPasswordSaving ? 'Resetting...' : 'Reset Password'}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
                {!profileModal.loading && !profileModal.error && !profileModal.data && (
                  <div className="text-sm text-gray-500 italic">No profile data available.</div>
                )}
                <div className="flex justify-end gap-2 mt-4">
                  <button 
                    onClick={() => {
                      setProfileModal({ open: false, loading: false, employee: null, data: null });
                      setProfileEditFields({ employee_id: '', hire_date: '', new_email: '', new_password: '' });
                    }} 
                    className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          )}

      {benefitsModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
          <div className="bg-white rounded-md shadow p-6 w-full max-w-lg">
            <h3 className="text-lg font-semibold mb-2">Set benefits: {benefitsModal.employee?.name}</h3>
            {benefitsModal.loading ? (
              <div className="text-sm text-gray-500">Loading...</div>
            ) : (
              <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
                {benefitsModal.rows.map((r, idx) => (
                  <div key={r.leave_type} className="flex items-center gap-3">
                    <div className="w-40 text-sm">{r.leave_type_name}</div>
                    <input
                      type="number"
                      min="0"
                      className="border rounded-md px-2 py-1 w-28"
                      value={r.entitled_days}
                      onChange={(e) => {
                        const v = e.target.value;
                        setBenefitsModal((prev) => {
                          const next = prev.rows.slice();
                          next[idx] = { ...next[idx], entitled_days: v };
                          return { ...prev, rows: next };
                        });
                      }}
                    />
                  </div>
                ))}
              </div>
            )}
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setBenefitsModal({ open: false, loading: false, employee: null, rows: [] })} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200" disabled={benefitsModal.loading}>Cancel</button>
              <button onClick={saveBenefits} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-sky-600 text-white bg-sky-600 hover:bg-sky-700" disabled={benefitsModal.loading}>{benefitsModal.loading ? 'Saving...' : 'Save'}</button>
            </div>
          </div>
        </div>
      )}

      {/* Leave History Modal */}
      {leaveHistoryModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
          <div className="bg-white rounded-md shadow p-6 w-full max-w-4xl max-h-[80vh] flex flex-col">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">Leave History: {leaveHistoryModal.employee?.name}</h3>
              <button
                onClick={() => setLeaveHistoryModal({ open: false, loading: false, employee: null, requests: [], searchQuery: '' })}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            {/* Search Bar */}
            {!leaveHistoryModal.loading && leaveHistoryModal.requests.length > 0 && (
              <div className="mb-4">
                <input
                  type="text"
                  placeholder="Search by leave type, reason, status, or dates..."
                  value={leaveHistoryModal.searchQuery}
                  onChange={(e) => setLeaveHistoryModal(prev => ({ ...prev, searchQuery: e.target.value }))}
                  className="w-full border rounded-md px-3 py-2 text-sm"
                />
              </div>
            )}
            
            {leaveHistoryModal.loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-2 text-sm text-gray-500">Loading leave history...</span>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto">
                {leaveHistoryModal.requests.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <p>No leave requests found for this employee.</p>
                  </div>
                ) : filteredLeaveHistory.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <p>No leave requests match your search criteria.</p>
                    <button 
                      onClick={() => setLeaveHistoryModal(prev => ({ ...prev, searchQuery: '' }))}
                      className="text-blue-600 hover:text-blue-800 text-sm mt-2"
                    >
                      Clear search
                    </button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Summary Stats */}
                    <div className="bg-gray-50 p-4 rounded-lg border">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                        <div>
                          <div className="text-2xl font-bold text-gray-900">{leaveHistoryModal.requests.length}</div>
                          <div className="text-sm text-gray-600">Total Requests</div>
                        </div>
                        <div>
                          <div className="text-2xl font-bold text-green-600">
                            {leaveHistoryModal.requests.filter(r => r.status === 'approved').length}
                          </div>
                          <div className="text-sm text-gray-600">Approved</div>
                        </div>
                        <div>
                          <div className="text-2xl font-bold text-yellow-600">
                            {leaveHistoryModal.requests.filter(r => ['pending', 'manager_approved', 'hr_approved'].includes(r.status)).length}
                          </div>
                          <div className="text-sm text-gray-600">Pending</div>
                        </div>
                        <div>
                          <div className="text-2xl font-bold text-red-600">
                            {leaveHistoryModal.requests.filter(r => r.status === 'rejected').length}
                          </div>
                          <div className="text-sm text-gray-600">Rejected</div>
                        </div>
                      </div>
                    </div>

                    {/* Leave Requests List */}
                    {filteredLeaveHistory.map((request) => (
                      <div key={request.id} className="border rounded-lg p-4 hover:bg-gray-50">
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex-1">
                            <h4 className="font-medium text-gray-900">
                              {request.leave_type_name || request.leave_type?.name || 'Unknown Leave Type'}
                            </h4>
                            <p className="text-sm text-gray-600 mt-1">
                              {request.start_date} to {request.end_date} ({request.total_days} days)
                            </p>
                            {request.reason && (
                              <p className="text-sm text-gray-600 mt-1">
                                <span className="font-medium">Reason:</span> {request.reason}
                              </p>
                            )}
                          </div>
                          <div className="flex flex-col items-end gap-2">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              request.status === 'approved' ? 'bg-green-100 text-green-800' :
                              request.status === 'rejected' ? 'bg-red-100 text-red-800' :
                              request.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                              request.status === 'manager_approved' ? 'bg-blue-100 text-blue-800' :
                              request.status === 'hr_approved' ? 'bg-purple-100 text-purple-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {request.status === 'manager_approved' ? 'Manager Approved' :
                               request.status === 'hr_approved' ? 'HR Approved' :
                               request.status?.charAt(0).toUpperCase() + request.status?.slice(1) || 'Unknown'}
                            </span>
                            {request.created_at && (
                              <span className="text-xs text-gray-500">
                                Requested: {new Date(request.created_at).toLocaleDateString()}
                              </span>
                            )}
                          </div>
                        </div>
                        
                        {request.approval_comments && (
                          <div className="mt-3 p-3 bg-gray-50 rounded border-l-4 border-blue-200">
                            <p className="text-sm">
                              <span className="font-medium text-gray-700">Comments:</span>
                              <span className="text-gray-600 ml-1">{request.approval_comments}</span>
                            </p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            <div className="flex justify-end mt-4 gap-2">
              <button
                onClick={handleExportLeaveHistoryCSV}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium border border-blue-600 text-white bg-blue-600 hover:bg-blue-700"
              >
                Download CSV
              </button>
              <button
                onClick={() => setLeaveHistoryModal({ open: false, loading: false, employee: null, requests: [], searchQuery: '' })}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium border border-gray-200 hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
      <div>
        <h3 className="text-lg font-medium mb-3">Staff Members ({staff.length})</h3>
        {staff.length === 0 ? (
          <div className="text-sm text-gray-500">No staff in this department.</div>
        ) : (
          <div className="overflow-x-auto bg-white rounded border">
            <table className="min-w-full text-sm text-left">
              <thead className="text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-3 py-2">#</th>
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2">Email</th>
                  <th className="px-3 py-2">Employee ID</th>
                  <th className="px-3 py-2">Role</th>
                  <th className="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {staff.map((s, idx) => (
                  <tr key={s.id} className="border-t">
                    <td className="px-3 py-2 align-top">{idx + 1}</td>
                    <td className="px-3 py-2 align-top">{s.name}</td>
                    <td className="px-3 py-2 align-top">{s.email}</td>
                    <td className="px-3 py-2 align-top">{s.employee_id}</td>
                    <td className="px-3 py-2 align-top">{s.role}</td>
                    <td className="px-3 py-2 align-top">
                      <div className="flex gap-2">
                          <button
                            onClick={() => openProfile({ id: s.id, name: s.name })}
                            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                          >
                            Profile
                          </button>
                          <button
                            onClick={() => openBenefits({ id: s.id, name: s.name })}
                            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                          >
                            Set benefits
                          </button>
                          <button
                            onClick={() => openLeaveHistory({ id: s.id, name: s.name })}
                            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-blue-200 text-blue-700 hover:bg-blue-50"
                          >
                            View Leave History
                          </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
      
    </>
  );
}

// HOD modal handling moved to AffiliatePage (handled on the department card)
