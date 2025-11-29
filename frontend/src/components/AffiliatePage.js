import React, { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';

const parseNumericId = (value) => {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null;
  }
  
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (trimmed === '') {
      return null;
    }
    const parsed = Number(trimmed);
    return Number.isNaN(parsed) ? null : parsed;
  }
  return null;
};

const mapStaffRecord = (staff, context = {}) => {
  const firstName = staff.first_name || '';
  const lastName = staff.last_name || '';
  const fallbackName = `${firstName} ${lastName}`.trim();

  const affiliateIdRaw = context.affiliateId ?? staff.affiliate?.id ?? staff.affiliate_id ?? null;
  const affiliateId = parseNumericId(affiliateIdRaw);
  const affiliateName = context.affiliateName ?? staff.affiliate?.name ?? staff.affiliate_name ?? null;
  const departmentName = context.department ?? staff.department?.name ?? staff.department_name ?? (typeof staff.department === 'string' ? staff.department : null) ?? null;

  return {
    id: staff.id,
    name: staff.name || fallbackName || staff.email || 'Staff member',
    email: staff.email || '',
    department: departmentName,
    employee_id: staff.employee_id,
    role: staff.role,
    manager: staff.manager,
    hire_date: staff.hire_date,
    affiliateId,
    affiliateName,
  };
};

const normalizeStaffPayload = (payload, affiliateContext = {}) => {
  const base = Array.isArray(payload?.results)
    ? payload.results
    : (Array.isArray(payload?.data)
      ? payload.data
      : (Array.isArray(payload) ? payload : []));

  if (!Array.isArray(base)) {
    return [];
  }

  const records = [];

  base.forEach((item) => {
    if (Array.isArray(item?.staff)) {
      const departmentName = item.name || item.department_name || (typeof item.department === 'string' ? item.department : null) || null;
      const affiliateDetails = {
        affiliateId: item.affiliate?.id ?? item.affiliate_id ?? affiliateContext.id ?? null,
        affiliateName: item.affiliate?.name ?? item.affiliate_name ?? affiliateContext.name ?? null,
      };
      item.staff.forEach((member) => {
        records.push(mapStaffRecord(member, { department: departmentName, ...affiliateDetails }));
      });
    } else if (item && (item.id || item.email || item.first_name || item.last_name)) {
      records.push(mapStaffRecord(item, {
        affiliateId: affiliateContext.id,
        affiliateName: affiliateContext.name,
      }));
    }
  });

  return records;
};

const stripAffiliateMeta = (records) => records.map(({ affiliateId, affiliateName, ...rest }) => rest);

export default function AffiliatePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [affiliate, setAffiliate] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [ceo, setCeo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newDeptModal, setNewDeptModal] = useState({ open: false, name: '', description: '' });
  const [deleteModal, setDeleteModal] = useState({ open: false, selected: {}, processing: false });
  const [hodModal, setHodModal] = useState({ open: false, loading: false, department: null, selectedManagerId: '' });
  const [newEmployeeModal, setNewEmployeeModal] = useState({ open: false, loading: false });

  // Local modals for SDSL/SBL staff actions (Profile, Benefits, Leave History)
  const [profileModal, setProfileModal] = useState({ open: false, loading: false, employee: null, data: null, error: null });
  const [benefitsModal, setBenefitsModal] = useState({ open: false, loading: false, employee: null, rows: [] });
  const [leaveHistoryModal, setLeaveHistoryModal] = useState({ open: false, loading: false, employee: null, requests: [], searchQuery: '' });
  const [profileEditFields, setProfileEditFields] = useState({ employee_id: '', hire_date: '', new_email: '', new_password: '', department_id: '' });
  const [profileFieldsSaving, setProfileFieldsSaving] = useState(false);
  const [profileRoleSaving, setProfileRoleSaving] = useState(false);
  const [resetPasswordSaving, setResetPasswordSaving] = useState(false);
  const [updateEmailSaving, setUpdateEmailSaving] = useState(false);
  const [selectedRole, setSelectedRole] = useState('');

  // Desired display order for departments (case-insensitive match)
  const desiredOrder = [
    'Finance & Accounts',
    'Government Securities',
    'Pensions & Provident Fund',
    'Private Wealth & Mutual Fund',
    'HR & Admin',
    'Client Service/Marketing',
    'Corporate Finance',
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
      const affiliateData = affRes.data;
      setAffiliate(affiliateData);

      // Resolve CEO for this affiliate: prefer affiliate.ceo, fallback to staff query
      if (affiliateData?.ceo) {
        setCeo({ name: affiliateData.ceo.name || affiliateData.ceo.email, email: affiliateData.ceo.email });
      } else {
        try {
          const ceoRes = await api.get(`/users/staff/?affiliate_id=${id}&role=ceo`);
          const ceoData = ceoRes.data?.results?.[0] || ceoRes.data?.[0];
          if (ceoData) {
            setCeo({ name: ceoData.name || [ceoData.first_name, ceoData.last_name].filter(Boolean).join(' ') || ceoData.email, email: ceoData.email });
          } else {
            setCeo(null);
          }
        } catch (e) {
          console.warn('Failed to load CEO for affiliate:', e);
          setCeo(null);
        }
      }
      let list = Array.isArray(deptRes.data?.results) ? deptRes.data.results : (deptRes.data || []);
      // Hide Executive pseudo-departments if any remain
      list = (list || []).filter((d) => {
        const n = (d?.name || '').toString().trim().toLowerCase();
        return !(n === 'executive' || n === 'executives');
      });
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

      let staffRecords = [];
      const affiliateIdForContext = parseNumericId(affiliateData?.id) ?? (affiliateData?.id ?? null);
      try {
        const staffRes = await api.get(`/users/staff/?affiliate_id=${id}`);
        staffRecords = normalizeStaffPayload(staffRes?.data, {
          id: affiliateIdForContext,
          name: affiliateData?.name,
        });
      } catch (_err) {
        try {
          const staffResAll = await api.get(`/users/staff/`);
          const allRecords = normalizeStaffPayload(staffResAll?.data);
          const deptNames = new Set(sorted.map((d) => (d?.name || '').toString()));
          const affiliateMatchId = parseNumericId(affiliateData?.id);
          const affiliateNameMatch = affiliateData?.name;
          staffRecords = allRecords.filter((record) => {
            const recordAffiliateId = parseNumericId(record.affiliateId);
            if (recordAffiliateId !== null && affiliateMatchId !== null) {
              return recordAffiliateId === affiliateMatchId;
            }
            if (record.affiliateName && affiliateNameMatch) {
              return record.affiliateName === affiliateNameMatch;
            }
            if (deptNames.size > 0 && record.department) {
              return deptNames.has(record.department);
            }
            return false;
          });
        } catch (_) {
          staffRecords = [];
        }
      }
  // Exclude CEO from employee cards to avoid duplication with top-right CEO display
  const filtered = staffRecords.filter((rec) => rec.role !== 'ceo');
  setEmployees(stripAffiliateMeta(filtered));
    } catch (e) {
      const msg = e.response?.data?.detail || e.response?.data?.error || 'Failed to load affiliate';
      showToast({ type: 'error', message: msg });
    } finally {
      setLoading(false);
    }
  };

  // --- Modal handlers for affiliate staff (copied/adapted from DepartmentPage) ---
  const openProfile = async (emp) => {
    if (!emp || !emp.id) return;
    console.log('[AffiliatePage] openProfile called for', emp);
    showToast({ type: 'info', message: `Opening profile for ${emp.name || emp.id}...` });
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
    console.log('[AffiliatePage] openBenefits called for', emp);
    showToast({ type: 'info', message: `Loading benefits for ${emp.name || emp.id}...` });
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
      if (!trimmedEmployeeId) { showToast({ type: 'error', message: 'Employee ID is required' }); return; }
      updates.employee_id = trimmedEmployeeId;
    }
    if (profileEditFields.hire_date !== (currentData.hire_date || '')) {
      updates.hire_date = profileEditFields.hire_date;
    }
    if (Object.keys(updates).length === 0) return;
    try {
      setProfileFieldsSaving(true);
      const res = await api.patch(`/users/${profileModal.employee.id}/`, updates);
      const updatedUser = res.data || {};
      showToast({ type: 'success', message: 'Profile updated successfully' });
      setProfileModal(prev => ({ ...prev, data: prev.data ? { ...prev.data, employee_id: updatedUser.employee_id, hire_date: updatedUser.hire_date } : prev.data }));
      setProfileEditFields(prev => ({ ...prev, employee_id: updatedUser.employee_id || '', hire_date: updatedUser.hire_date || '' }));
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
    console.log('[AffiliatePage] openLeaveHistory called for', emp);
    showToast({ type: 'info', message: `Loading leave history for ${emp.name || emp.id}...` });
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
    const usFormat = (val) => {
      if (!val) return '';
      const s = String(val).split('T')[0];
      if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
        const [y, m, d] = s.split('-');
        return `${m}/${d}/${y}`;
      }
      const dt = new Date(val);
      if (!isNaN(dt)) {
        const mm = String(dt.getMonth() + 1).padStart(2, '0');
        const dd = String(dt.getDate()).padStart(2, '0');
        const yy = dt.getFullYear();
        return `${mm}/${dd}/${yy}`;
      }
      return String(val);
    };

    const csvRows = [
      ['Leave Type', 'Start Date', 'End Date', 'Days', 'Status', 'Reason', 'Comments', 'Requested At', 'Final Actor Role', 'Final Actor Timestamp'],
    ];
    requests.forEach(request => {
      // compute final actor role and timestamp
      const mgr = request.manager_approval_date || null;
      const hr = request.hr_approval_date || null;
      const ceo = request.ceo_approval_date || null;
      const rej = request.rejection_date || null;
      const candidates = [
        { role: 'CEO', date: ceo, verb: 'approved' },
        { role: 'HR', date: hr, verb: 'approved' },
        { role: 'Manager', date: mgr, verb: 'approved' },
        { role: 'Rejected', date: rej, verb: 'rejected' },
      ].filter(c => c.date);
      let finalRole = '';
      let finalTs = '';
      if (candidates.length) {
        candidates.sort((a, b) => new Date(b.date) - new Date(a.date));
        finalRole = `${candidates[0].role} ${candidates[0].verb}`;
        finalTs = new Date(candidates[0].date).toISOString();
      }
      csvRows.push([
        request.leave_type_name || request.leave_type?.name || 'Unknown',
        usFormat(request.start_date),
        usFormat(request.end_date),
        request.total_days,
        request.status,
        request.reason || '',
        request.approval_comments || '',
        usFormat(request.created_at),
        finalRole,
        finalTs,
      ]);
    });
    const csvContent = csvRows.map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
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

  const handleExportAffiliateStaffCSV = async () => {
    try {
      showToast({ type: 'info', message: 'Exporting affiliate staff...' });
      const res = await api.get(`/users/staff/?affiliate_id=${id}`);
      const base = Array.isArray(res.data?.results) ? res.data.results : (Array.isArray(res.data) ? res.data : []);
      const rows = base.map((s) => ({ name: s.name || `${s.first_name || ''} ${s.last_name || ''}`.trim(), email: s.email, employee_id: s.employee_id, role: s.role }));
      const headers = ['name', 'email', 'employee_id', 'role'];
      const csv = [headers.join(','), ...rows.map(r => `${r.name},${r.email},${r.employee_id || ''},${r.role || ''}`)].join('\n');
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(affiliate?.name || 'affiliate').replace(/[^a-z0-9\-]/gi, '_')}_staff.csv`;
      a.click();
      URL.revokeObjectURL(url);
      showToast({ type: 'success', message: 'Affiliate staff exported' });
    } catch (e) {
      console.error('Failed to export affiliate staff', e);
      showToast({ type: 'error', message: 'Failed to export affiliate staff' });
    }
  };

  const handleExportAffiliateLeaveRequestsCSV = async () => {
    try {
      showToast({ type: 'info', message: 'Fetching leave requests...' });
      const res = await api.get(`/leaves/requests/?employee_affiliate_id=${id}&limit=1000`);
      const base = Array.isArray(res.data?.results) ? res.data.results : (Array.isArray(res.data) ? res.data : []);
      if (!base.length) {
        showToast({ type: 'info', message: 'No leave requests found for this affiliate' });
        return;
      }
      const headers = ['id', 'employee_name', 'employee_email', 'start_date', 'end_date', 'status', 'status_display', 'final_actor_role', 'final_actor_timestamp'];
      const rows = base.map((r) => {
        // compute final actor
        const mgr = r.manager_approval_date || null;
        const hr = r.hr_approval_date || null;
        const ceo = r.ceo_approval_date || null;
        const rej = r.rejection_date || null;
        const candidates = [
          { role: 'CEO', date: ceo, verb: 'approved' },
          { role: 'HR', date: hr, verb: 'approved' },
          { role: 'Manager', date: mgr, verb: 'approved' },
          { role: 'Rejected', date: rej, verb: 'rejected' },
        ].filter(c => c.date);
        let finalRole = '';
        let finalTs = '';
        if (candidates.length) {
          candidates.sort((a, b) => new Date(b.date) - new Date(a.date));
          finalRole = `${candidates[0].role} ${candidates[0].verb}`;
          finalTs = new Date(candidates[0].date).toISOString();
        }
        return {
          id: r.id,
          employee_name: r.employee_name || r.name || '',
          employee_email: r.employee_email || r.email || '',
          start_date: r.start_date || '',
          end_date: r.end_date || '',
          status: r.status || '',
          status_display: r.status_display || r.get_dynamic_status_display || '',
          finalRole,
          finalTs,
        };
      });
      const csv = [headers.join(','), ...rows.map(row => `${row.id},"${row.employee_name}",${row.employee_email},${row.start_date},${row.end_date},${row.status},"${row.status_display}","${row.finalRole}",${row.finalTs}`)].join('\n');
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(affiliate?.name || 'affiliate').replace(/[^a-z0-9\-]/gi, '_')}_leave_requests.csv`;
      a.click();
      URL.revokeObjectURL(url);
      showToast({ type: 'success', message: 'Affiliate leave requests exported' });
    } catch (e) {
      console.error('Failed to export affiliate leave requests', e);
      showToast({ type: 'error', message: 'Failed to export affiliate leave requests' });
    }
  };

  // Filtered leave history: date-aware search and show last 5 by default
  const filteredLeaveHistory = React.useMemo(() => {
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

    if (!query) return requests.slice(0, 5);

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

  useEffect(() => {
    load();
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
        <div className="flex items-center gap-4">
          {/* CEO Display */}
          {ceo && (
            <div className="text-right">
              <div className="text-sm font-medium text-gray-900">
                CEO: {ceo.name}
              </div>
              <div className="text-xs text-gray-500">
                {ceo.email}
              </div>
            </div>
          )}
          
          <div className="flex items-center gap-2">
            {/* New Employee Button */}
            <button
              onClick={() => setNewEmployeeModal({ open: true, loading: false })}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700"
            >
              New Employee
            </button>
              {(affiliate.name || '').toUpperCase() === 'SDSL' || (affiliate.name || '').toUpperCase() === 'SBL' ? (
                <>
                  <button onClick={handleExportAffiliateStaffCSV} className="inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium border border-gray-200">Export Staff</button>
                  <button onClick={handleExportAffiliateLeaveRequestsCSV} className="inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium border border-blue-200 text-blue-700 hover:bg-blue-50">Export Leave Requests</button>
                </>
              ) : null}
            
            {/* Only show department management for MERBAN CAPITAL */}
            {(affiliate?.name || '').toUpperCase() === 'MERBAN CAPITAL' && (
              <>
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
              </>
            )}
          </div>
        </div>
      </div>

      {/* MERBAN CAPITAL: Show departments */}
      {(affiliate.name || '').toUpperCase() === 'MERBAN CAPITAL' && (
        <div className="bg-white shadow rounded-md p-4">
          <h2 className="text-lg font-medium mb-4">Departments</h2>
          {departments.length === 0 ? (
            <div className="text-sm text-gray-500">No departments under this affiliate yet.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {departments.map((d) => (
              <div
                key={d.id}
                onClick={() => navigate(`/staff/departments/${d.id}`)}
                role="button"
                title={`Open ${d.name}`}
                className="border border-gray-200 rounded-lg overflow-hidden bg-white hover:shadow-md cursor-pointer"
              >
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
                        onClick={(e) => { e.stopPropagation(); openHodModal(d); }}
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
      )}

      {/* SDSL/SBL: Show individual employees */}
      {((affiliate.name || '').toUpperCase() === 'SDSL' || (affiliate.name || '').toUpperCase() === 'SBL') && (
        <div className="bg-white shadow rounded-md p-4">
          <h2 className="text-lg font-medium mb-3">Team Members ({employees.length})</h2>
          {employees.length === 0 ? (
            <div className="text-sm text-gray-500">No team members under this affiliate yet.</div>
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
                  {employees.map((s, idx) => (
                    <tr key={s.id} className="border-t">
                      <td className="px-3 py-2 align-top">{idx + 1}</td>
                      <td className="px-3 py-2 align-top">{s.name}</td>
                      <td className="px-3 py-2 align-top">{s.email}</td>
                      <td className="px-3 py-2 align-top">{s.employee_id}</td>
                      <td className="px-3 py-2 align-top">{s.role}</td>
                      <td className="px-3 py-2 align-top">
                        <div className="flex gap-2">
                          <button onClick={() => openProfile({ id: s.id, name: s.name })} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200">Profile</button>
                          <button onClick={() => openBenefits({ id: s.id, name: s.name })} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200">Set benefits</button>
                          <button onClick={() => openLeaveHistory({ id: s.id, name: s.name })} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-blue-200 text-blue-700 hover:bg-blue-50">View Leave History</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

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

      {/* New Employee Modal */}
      {/* Profile / Benefits / Leave History modals for affiliate staff */}
      {profileModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
          <div className="bg-white rounded-md shadow p-6 w-full max-w-lg max-h-[90vh] flex flex-col">
            <h3 className="text-lg font-semibold mb-2">Profile: {profileModal.employee?.name}</h3>
            {profileModal.loading && (<div className="text-sm text-gray-500">Loading...</div>)}
            {!profileModal.loading && profileModal.error && (
              <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-3 mb-2">{profileModal.error}</div>
            )}
            {!profileModal.loading && !profileModal.error && profileModal.data && (
              <div className="space-y-4 text-sm flex-1 overflow-y-auto">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Employee ID</label>
                  <input type="text" value={profileEditFields.employee_id} onChange={(e) => setProfileEditFields(prev => ({ ...prev, employee_id: e.target.value }))} className="border rounded-md px-2 py-1 text-sm w-full" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Email</label>
                  <div className="text-sm"><span className="font-medium">Current:</span> {profileModal.data.email || '—'}</div>
                  <div className="mt-2 flex gap-2">
                    <input type="email" value={profileEditFields.new_email} onChange={(e) => setProfileEditFields(prev => ({ ...prev, new_email: e.target.value }))} className="border rounded-md px-2 py-1 text-sm flex-1" placeholder="Enter new email" />
                    <button onClick={updateEmployeeEmail} disabled={updateEmailSaving || !profileEditFields.new_email} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border border-blue-600 text-white bg-blue-600 disabled:opacity-50">{updateEmailSaving ? 'Updating...' : 'Update Email'}</button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Hire Date</label>
                  <input type="date" value={profileEditFields.hire_date} onChange={(e) => setProfileEditFields(prev => ({ ...prev, hire_date: e.target.value }))} className="border rounded-md px-2 py-1 text-sm w-full" />
                </div>

                <div className="flex justify-end">
                  <button onClick={saveProfileFields} disabled={profileFieldsSaving} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border border-green-600 text-white bg-green-600 disabled:opacity-50">{profileFieldsSaving ? 'Saving...' : 'Save Profile Changes'}</button>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Role</label>
                  <div className="flex items-center gap-2">
                    <select value={selectedRole || profileModal.data.role || 'junior_staff'} onChange={(e) => setSelectedRole(e.target.value)} className="border rounded-md px-2 py-1 text-sm">
                      <option value="junior_staff">Junior Staff</option>
                      <option value="senior_staff">Senior Staff</option>
                      <option value="manager">Head of Department</option>
                      <option value="hr">HR</option>
                      <option value="ceo">CEO</option>
                      <option value="admin">Admin</option>
                    </select>
                    <button onClick={saveProfileRole} disabled={profileRoleSaving || (profileModal.data.role || 'junior_staff') === selectedRole} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border border-sky-600 text-white bg-sky-600 disabled:opacity-50">{profileRoleSaving ? 'Saving...' : 'Save Role'}</button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Reset Password</label>
                  <div className="flex gap-2">
                    <input type="password" value={profileEditFields.new_password} onChange={(e) => setProfileEditFields(prev => ({ ...prev, new_password: e.target.value }))} className="border rounded-md px-2 py-1 text-sm flex-1" placeholder="Enter new password (min 8 chars)" />
                    <button onClick={resetEmployeePassword} disabled={resetPasswordSaving || !profileEditFields.new_password} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border border-red-600 text-white bg-red-600 disabled:opacity-50">{resetPasswordSaving ? 'Resetting...' : 'Reset Password'}</button>
                  </div>
                </div>
              </div>
            )}
            <div className="flex-shrink-0 flex justify-end gap-2 mt-4 bg-white">
              <button onClick={() => setProfileModal({ open: false, loading: false, employee: null, data: null, error: null })} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200">Close</button>
            </div>
          </div>
        </div>
      )}

      {benefitsModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
          <div className="bg-white rounded-md shadow p-6 w-full max-w-lg max-h-[90vh] flex flex-col">
            <h3 className="text-lg font-semibold mb-2">Set benefits: {benefitsModal.employee?.name}</h3>
            {benefitsModal.loading ? (
              <div className="text-sm text-gray-500">Loading...</div>
            ) : (
              <div className="space-y-3 overflow-y-auto flex-1 pr-1">
                {benefitsModal.rows.map((r, idx) => (
                  <div key={r.leave_type} className="flex items-center gap-3">
                    <div className="w-40 text-sm">{r.leave_type_name}</div>
                    <input type="number" min="0" className="border rounded-md px-2 py-1 w-28" value={r.entitled_days} onChange={(e) => { const v = e.target.value; setBenefitsModal((prev) => { const next = prev.rows.slice(); next[idx] = { ...next[idx], entitled_days: v }; return { ...prev, rows: next }; }); }} />
                  </div>
                ))}
              </div>
            )}
            <div className="flex-shrink-0 flex justify-end gap-2 mt-4 bg-white">
              <button onClick={() => setBenefitsModal({ open: false, loading: false, employee: null, rows: [] })} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200" disabled={benefitsModal.loading}>Cancel</button>
              <button onClick={saveBenefits} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-sky-600 text-white bg-sky-600 hover:bg-sky-700" disabled={benefitsModal.loading}>{benefitsModal.loading ? 'Saving...' : 'Save'}</button>
            </div>
          </div>
        </div>
      )}

      {leaveHistoryModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
          <div className="bg-white rounded-md shadow p-6 w-full max-w-4xl max-h-[80vh] flex flex-col">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">Leave History: {leaveHistoryModal.employee?.name}</h3>
              <button onClick={() => setLeaveHistoryModal({ open: false, loading: false, employee: null, requests: [], searchQuery: '' })} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            {!leaveHistoryModal.loading && leaveHistoryModal.requests.length > 0 && (
              <div className="mb-4">
                <input type="text" placeholder="Search by leave type, reason, status, or dates..." value={leaveHistoryModal.searchQuery} onChange={(e) => setLeaveHistoryModal(prev => ({ ...prev, searchQuery: e.target.value }))} className="w-full border rounded-md px-3 py-2 text-sm" />
              </div>
            )}
            {leaveHistoryModal.loading ? (
              <div className="flex items-center justify-center py-8"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div><span className="ml-2 text-sm text-gray-500">Loading leave history...</span></div>
            ) : (
              <div className="flex-1 overflow-y-auto">
                {leaveHistoryModal.requests.length === 0 ? (
                  <div className="text-center py-8 text-gray-500"><p>No leave requests found for this employee.</p></div>
                ) : (
                  <div className="space-y-4">
                    <div className="bg-gray-50 p-4 rounded-lg border">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                        <div><div className="text-2xl font-bold text-gray-900">{leaveHistoryModal.requests.length}</div><div className="text-sm text-gray-600">Total Requests</div></div>
                        <div><div className="text-2xl font-bold text-green-600">{leaveHistoryModal.requests.filter(r => r.status === 'approved').length}</div><div className="text-sm text-gray-600">Approved</div></div>
                        <div><div className="text-2xl font-bold text-yellow-600">{leaveHistoryModal.requests.filter(r => ['pending','manager_approved','hr_approved'].includes(r.status)).length}</div><div className="text-sm text-gray-600">Pending</div></div>
                        <div><div className="text-2xl font-bold text-red-600">{leaveHistoryModal.requests.filter(r => r.status === 'rejected').length}</div><div className="text-sm text-gray-600">Rejected</div></div>
                      </div>
                    </div>
                    {leaveHistoryModal.requests.map((request) => (
                      <div key={request.id} className="border rounded-lg p-4 hover:bg-gray-50">
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex-1">
                            <h4 className="font-medium text-gray-900">{request.leave_type_name || request.leave_type?.name || 'Unknown'}</h4>
                            <p className="text-sm text-gray-600 mt-1">{request.start_date} to {request.end_date} ({request.total_days} days)</p>
                            {request.reason && <p className="text-sm text-gray-600 mt-1"><span className="font-medium">Reason:</span> {request.reason}</p>}
                            {/* final approver/rejector */}
                            {(() => {
                              const mgr = request.manager_approval_date || null;
                              const hr = request.hr_approval_date || null;
                              const ceo = request.ceo_approval_date || null;
                              const rej = request.rejection_date || null;
                              const candidates = [
                                { role: 'CEO', date: ceo },
                                { role: 'HR', date: hr },
                                { role: 'Manager', date: mgr },
                                { role: 'Rejected', date: rej },
                              ].filter(c => c.date);
                              if (candidates.length) {
                                candidates.sort((a, b) => new Date(b.date) - new Date(a.date));
                                const top = candidates[0];
                                return <p className="text-sm text-gray-600 mt-2"><span className="font-medium">Final:</span> {top.role} {top.role === 'Rejected' ? 'rejected' : 'approved'} {new Date(top.date).toLocaleString()}</p>;
                              }
                              return null;
                            })()}
                          </div>
                          <div className="flex flex-col items-end gap-2">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${request.status === 'approved' ? 'bg-green-100 text-green-800' : request.status === 'rejected' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'}`}>{request.status}</span>
                            {request.created_at && <span className="text-xs text-gray-500">Requested: {new Date(request.created_at).toLocaleDateString()}</span>}
                          </div>
                        </div>
                        {request.approval_comments && (<div className="mt-3 p-3 bg-gray-50 rounded border-l-4 border-blue-200"><p className="text-sm"><span className="font-medium text-gray-700">Comments:</span><span className="text-gray-600 ml-1">{request.approval_comments}</span></p></div>)}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            <div className="flex justify-end mt-4 gap-2">
              <button onClick={handleExportLeaveHistoryCSV} className="inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium border border-blue-600 text-white bg-blue-600 hover:bg-blue-700">Download CSV</button>
              <button onClick={() => setLeaveHistoryModal({ open: false, loading: false, employee: null, requests: [], searchQuery: '' })} className="inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium border border-gray-200 hover:bg-gray-50">Close</button>
            </div>
          </div>
        </div>
      )}

      {newEmployeeModal.open && (
        <NewEmployeeModal
          affiliate={affiliate}
          departments={departments}
          onClose={() => setNewEmployeeModal({ open: false, loading: false })}
          onSuccess={() => {
            setNewEmployeeModal({ open: false, loading: false });
            load(); // Refresh data
          }}
        />
      )}
    </div>
  );
}

// New Employee Modal Component
function NewEmployeeModal({ affiliate, departments, onClose, onSuccess }) {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    employee_id: '',
    department_id: '',
    role: 'junior_staff',
    hire_date: new Date().toISOString().split('T')[0],
    password: ''
  });

  // No grade fetching; roles fully replace grades

  const handleSubmit = async (e) => {
    e.preventDefault();
    // Client-side validation
    const nextErrors = {};
    if (!formData.first_name.trim()) nextErrors.first_name = 'First name is required';
    if (!formData.last_name.trim()) nextErrors.last_name = 'Last name is required';
    if (!formData.email.trim()) nextErrors.email = 'Email is required';
    if (!formData.password || formData.password.length < 8) nextErrors.password = 'Password must be at least 8 characters';
    if ((affiliate?.name || '').toUpperCase() === 'MERBAN CAPITAL' && !formData.department_id) nextErrors.department_id = 'Department is required for Merban Capital';
  // roles replace grades; no grade required
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setLoading(true);
    try {
      const payload = {
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim(),
        email: formData.email.trim(),
        role: formData.role,
        hire_date: formData.hire_date,
        password: formData.password,
        affiliate_id: Number(affiliate.id),
        // Only include department_id for MERBAN CAPITAL
        ...((affiliate?.name || '').toUpperCase() === 'MERBAN CAPITAL' && formData.department_id ? { department_id: Number(formData.department_id) } : {}),
      };

      if (formData.employee_id.trim()) {
        payload.employee_id = formData.employee_id.trim();
      }

      await api.post('/users/staff/', payload);
      showToast({ type: 'success', message: 'Employee created successfully!' });
      onSuccess();
    } catch (error) {
      console.error('Error creating employee:', error);
      showToast({ 
        type: 'error', 
        message: error.response?.data?.detail || error.response?.data?.error || 'Failed to create employee' 
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
      <div className="bg-white rounded-lg shadow-lg p-6 w-full max-w-lg max-h-[90vh] flex flex-col">
        <h3 className="text-lg font-semibold mb-4">Add New Employee - {affiliate.name}</h3>
        
        <form onSubmit={handleSubmit} className="space-y-4 flex-1 overflow-y-auto">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">First Name *</label>
              <input
                type="text"
                value={formData.first_name}
                onChange={(e) => setFormData(prev => ({ ...prev, first_name: e.target.value }))}
                className={`w-full border rounded-md px-3 py-2 ${errors.first_name ? 'border-red-500' : ''}`}
                required
                disabled={loading}
              />
              {errors.first_name && <p className="mt-1 text-xs text-red-600">{errors.first_name}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Last Name *</label>
              <input
                type="text"
                value={formData.last_name}
                onChange={(e) => setFormData(prev => ({ ...prev, last_name: e.target.value }))}
                className={`w-full border rounded-md px-3 py-2 ${errors.last_name ? 'border-red-500' : ''}`}
                required
                disabled={loading}
              />
              {errors.last_name && <p className="mt-1 text-xs text-red-600">{errors.last_name}</p>}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
              className={`w-full border rounded-md px-3 py-2 ${errors.email ? 'border-red-500' : ''}`}
              required
              disabled={loading}
            />
            {errors.email && <p className="mt-1 text-xs text-red-600">{errors.email}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Employee ID</label>
            <input
              type="text"
              value={formData.employee_id}
              onChange={(e) => setFormData(prev => ({ ...prev, employee_id: e.target.value }))}
              className="w-full border rounded-md px-3 py-2"
              disabled={loading}
              placeholder="Auto-generated if left blank"
            />
          </div>

          {/* Show department dropdown only for MERBAN CAPITAL (moved to after Employee ID per request) */}
          {(affiliate?.name || '').toUpperCase() === 'MERBAN CAPITAL' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Department *</label>
              <select
                value={formData.department_id}
                onChange={(e) => setFormData(prev => ({ ...prev, department_id: e.target.value }))}
                className={`w-full border rounded-md px-3 py-2 ${errors.department_id ? 'border-red-500' : ''}`}
                required
                disabled={loading}
              >
                <option value="">Select Department</option>
                {departments.map(dept => (
                  <option key={dept.id} value={dept.id}>{dept.name}</option>
                ))}
              </select>
              {errors.department_id && <p className="mt-1 text-xs text-red-600">{errors.department_id}</p>}
            </div>
          )}

          {/* For SDSL/SBL, show as individual entity */}
          {(affiliate.name === 'SDSL' || affiliate.name === 'SBL') && (
            <div className="bg-blue-50 p-3 rounded-md">
              <p className="text-sm text-blue-700">
                This employee will be added as an individual entity under {affiliate.name} (no department assignment).
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
              <select
                value={formData.role}
                onChange={(e) => setFormData(prev => ({ ...prev, role: e.target.value }))}
                className="w-full border rounded-md px-3 py-2"
                disabled={loading}
              >
                <option value="junior_staff">Junior Staff</option>
                <option value="senior_staff">Senior Staff</option>
                <option value="manager">HOD</option>
                <option value="hr">HR</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Hire Date</label>
              <input
                type="date"
                value={formData.hire_date}
                onChange={(e) => setFormData(prev => ({ ...prev, hire_date: e.target.value }))}
                className="w-full border rounded-md px-3 py-2"
                disabled={loading}
              />
            </div>
          </div>

          {/* No grade selection; role dropdown above handles classification */}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password *</label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
              className={`w-full border rounded-md px-3 py-2 ${errors.password ? 'border-red-500' : ''}`}
              required
              disabled={loading}
              placeholder="Minimum 8 characters"
            />
            {errors.password && <p className="mt-1 text-xs text-red-600">{errors.password}</p>}
          </div>

          <div className="flex-shrink-0 flex justify-end gap-2 pt-4 bg-white">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium border border-gray-300 rounded-md hover:bg-gray-50"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              disabled={loading}
            >
              {loading ? 'Creating...' : 'Create Employee'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
