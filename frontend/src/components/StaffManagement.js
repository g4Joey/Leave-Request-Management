import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { useAuth } from '../contexts/AuthContext';
import RoleManagement from './RoleManagement';

// Base sidebar items (grade-entitlements will be conditionally included for privileged roles)
// Added Affiliates tab to the top per request
const BASE_SIDEBAR_ITEMS = [
  { id: 'affiliates', label: 'Affiliates' },
  // Departments tab hidden per request; departments are managed under Affiliates now
  // { id: 'departments', label: 'Departments' },
  { id: 'employees', label: 'Employees' },
  { id: 'leave-types', label: 'Leave Types' },
  { id: 'leave-policies', label: 'Leave Policies' },
  { id: 'import', label: 'Import' },
  { id: 'export', label: 'Export' },
];

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

function StaffManagement() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { user } = useAuth();
  const canManageGradeEntitlements = useMemo(() => {
    if (!user) return false;
    return user.is_superuser || ['hr','admin'].includes(user.role);
  }, [user]);

  // Build sidebar items dynamically (hide Role Management unless privileged)
  const SIDEBAR_ITEMS = useMemo(() => {
    const items = [...BASE_SIDEBAR_ITEMS];
    if (canManageGradeEntitlements) {
      items.push({ id: 'role-management', label: 'Role Management' });
    }
    return items;
  }, [canManageGradeEntitlements]);
  const [departments, setDepartments] = useState([]);
  const [affiliates, setAffiliates] = useState([]);
  const [affiliateInfo, setAffiliateInfo] = useState({}); // { [id]: { ceo: string|null, depts: number, members: number } }
  const [loading, setLoading] = useState(true);
  const [expandedDepts, setExpandedDepts] = useState({});
  // Default to Affiliates since the standalone Departments tab is hidden
  const [active, setActive] = useState('affiliates');
  const [employees, setEmployees] = useState([]);
  const [employeeQuery, setEmployeeQuery] = useState('');
  const fileInputRef = useRef(null);
  const [leaveTypeModal, setLeaveTypeModal] = useState({ open: false, name: '', id: null, value: '' , loading: false});
  const [profileModal, setProfileModal] = useState({ open: false, loading: false, employee: null, data: null, error: null });
  const [profileRoleSaving, setProfileRoleSaving] = useState(false);
  const [profileEditFields, setProfileEditFields] = useState({ employee_id: '', hire_date: '', new_email: '', new_password: '' });
  const [profileFieldsSaving, setProfileFieldsSaving] = useState(false);
  const [resetPasswordSaving, setResetPasswordSaving] = useState(false);
  const [updateEmailSaving, setUpdateEmailSaving] = useState(false);
  const [benefitsModal, setBenefitsModal] = useState({ open: false, loading: false, employee: null, rows: [] });
  const [leaveHistoryModal, setLeaveHistoryModal] = useState({ open: false, loading: false, employee: null, requests: [], searchQuery: '' });
  const [newDepartmentModal, setNewDepartmentModal] = useState({ open: false, loading: false, name: '', description: '' });
  const [newAffiliateModal, setNewAffiliateModal] = useState({ open: false, loading: false, name: '', description: '' });
  const [deleteEmployeeModal, setDeleteEmployeeModal] = useState({ open: false, selected: {}, processing: false });
  const [deleteAffiliateModal, setDeleteAffiliateModal] = useState({ open: false, selected: {}, processing: false });
  const [hodModal, setHodModal] = useState({ open: false, loading: false, department: null, selectedManagerId: '' });
  const [newEmployeeModal, setNewEmployeeModal] = useState({ 
    open: false, 
    loading: false, 
    username: '', 
    email: '', 
    first_name: '', 
    last_name: '', 
    employee_id: '', 
    role: 'junior_staff', 
    department_id: '', 
    password: '',
    hire_date: ''
  });

  // Remove trailing role words accidentally saved in last names (e.g., "Ato HOD")
  const cleanName = (name) => {
    if (!name || typeof name !== 'string') return name;
    return name.replace(/\s+(Manager|HOD|Staff|HR|Admin)$/i, '').trim();
  };

  const fetchStaffData = useCallback(async () => {
    try {
      // Fetch departments/employees
      const response = await api.get('/users/staff/');
      const payload = response?.data;
      
      // Handle simple array format (original structure)
      const depts = Array.isArray(payload)
        ? payload
        : (Array.isArray(payload?.results) ? payload.results : (Array.isArray(payload?.data) ? payload.data : []));

      // Coerce shapes defensively
      const safeDepts = (depts || []).map((d) => ({
        ...d,
        staff: Array.isArray(d?.staff) ? d.staff : [],
      }));

      // Hide Executive(s) pseudo-departments in UI lists
      const filteredDepts = safeDepts.filter((d) => {
        const n = (d?.name || '').toString().trim().toLowerCase();
        return !(n === 'executive' || n === 'executives');
      });
      setDepartments(filteredDepts);

      // Flatten employees for the Employees tab with CEO normalization and de-duplication
      const byId = new Map();
      safeDepts.forEach((d) => {
        const deptName = (d?.name || '').toString();
        (d.staff || []).forEach((s) => {
          // Normalize department for CEOs and for pseudo "Executive(s)" department labels
          const roleNorm = (s.role === 'employee' || s.role === 'staff') ? 'junior_staff' : (s.role === 'hod' ? 'manager' : s.role);
          const isCeo = roleNorm === 'ceo';
          const isExecDept = /^executive(s)?$/i.test(deptName);
          const deptDisplay = isCeo || isExecDept ? '—' : deptName;

          const record = {
            id: s.id,
            name: cleanName(s.name),
            email: s.email,
            department: deptDisplay,
            employee_id: s.employee_id,
            role: roleNorm,
            manager: s.manager,
            hire_date: s.hire_date,
          };
          byId.set(s.id, record); // last write wins; ensures uniqueness per user id
        });
      });
      
      // Fetch and include CEOs separately since they're excluded from department staff
      try {
        const ceoRes = await api.get('/users/staff/?role=ceo');
        const ceoData = ceoRes.data?.results || ceoRes.data || [];
        ceoData.forEach((ceo) => {
          if (ceo && ceo.id) {
            const ceoRecord = {
              id: ceo.id,
              name: cleanName(ceo.name || `${ceo.first_name || ''} ${ceo.last_name || ''}`.trim()),
              email: ceo.email,
              department: '—', // CEOs don't have departments
              employee_id: ceo.employee_id,
              role: 'ceo',
              manager: null,
              hire_date: ceo.hire_date,
            };
            byId.set(ceo.id, ceoRecord);
          }
        });
      } catch (ceoError) {
        console.warn('Failed to load CEOs:', ceoError);
      }
      
      setEmployees(Array.from(byId.values()));

  // Affiliates removed
    } catch (error) {
      console.error('Error fetching staff data:', error);
      showToast({
        type: 'error',
        message: 'Failed to load staff information. Please try again.'
      });
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    fetchStaffData();
  }, [fetchStaffData]);

  // Fetch affiliates for the Affiliates tab (HR only)
  const fetchAffiliates = useCallback(async () => {
    try {
      const res = await api.get('/users/affiliates/');
      const list = Array.isArray(res.data?.results) ? res.data.results : (res.data || []);
      setAffiliates(list);
    } catch (e) {
      // Non-fatal; keep silent to avoid noise on non-HR sessions
      console.warn('Failed to load affiliates', e.response?.data || e.message);
      setAffiliates([]);
    }
  }, []);

  useEffect(() => {
    fetchAffiliates();
  }, [fetchAffiliates]);

  // After affiliates load, fetch quick counts and CEO summary for each
  useEffect(() => {
    const loadQuickInfo = async () => {
      if (!Array.isArray(affiliates) || affiliates.length === 0) {
        setAffiliateInfo({});
        return;
      }
      try {
        const entries = await Promise.all(affiliates.map(async (aff) => {
          try {
            // CEO name - more robust name detection
            const ceoRes = await api.get(`/users/staff/?affiliate_id=${aff.id}&role=ceo`);
            const ceoItem = ceoRes.data?.results?.[0] || ceoRes.data?.[0] || null;
            let ceoName = null;
            if (ceoItem) {
              // Try multiple name sources in order of preference
              if (ceoItem.name && ceoItem.name.trim()) {
                ceoName = ceoItem.name.trim();
              } else if (ceoItem.first_name || ceoItem.last_name) {
                ceoName = [ceoItem.first_name, ceoItem.last_name].filter(Boolean).join(' ').trim();
              } else if (ceoItem.email) {
                // Fallback to email prefix if no name available
                ceoName = ceoItem.email.split('@')[0];
              }
            }
            // Departments (for Merban) and staff counts
            const deptRes = await api.get(`/users/departments/?affiliate_id=${aff.id}`);
            const allDepartments = Array.isArray(deptRes.data?.results) ? deptRes.data.results : (deptRes.data || []);
            // Filter out Executive departments from count
            const departments = allDepartments.filter((d) => {
              const n = (d?.name || '').toString().trim().toLowerCase();
              return !(n === 'executive' || n === 'executives');
            });
            let memberCount = 0;
            try {
              const staffRes = await api.get(`/users/staff/?affiliate_id=${aff.id}`);
              const normalized = normalizeStaffPayload(staffRes?.data, {
                id: parseNumericId(aff.id) ?? aff.id ?? null,
                name: aff.name,
              });
              // Include CEO in member counts
              const ceoCount = ceoName ? 1 : 0;
              memberCount = normalized.length + ceoCount;
            } catch (_) {
              memberCount = ceoName ? 1 : 0;
            }
            return [aff.id, { ceo: ceoName, depts: departments.length, members: memberCount }];
          } catch (e) {
            return [aff.id, { ceo: null, depts: 0, members: 0 }];
          }
        }));
        setAffiliateInfo(Object.fromEntries(entries));
      } catch (e) {
        console.warn('Failed to load affiliate quick info', e);
        setAffiliateInfo({});
      }
    };
    loadQuickInfo();
  }, [affiliates]);



  // Force refresh data when component becomes visible
  useEffect(() => {
    const handleFocus = () => fetchStaffData();
    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, [fetchStaffData]);





  const openProfile = async (emp) => {
    if (!emp || !emp.id) {
      showToast({ type: 'error', message: 'Invalid employee record – missing ID' });
      console.error('openProfile called with invalid employee object:', emp);
      return;
    }
    console.log('[StaffManagement] Opening profile for employee:', emp);
    setProfileModal({ open: true, loading: true, employee: emp, data: null, error: null });
    try {
      const res = await api.get(`/users/${emp.id}/`);
      console.log('[StaffManagement] Raw profile response:', res.data);
      const raw = res.data || {};
      const normalized = {
        id: raw.id,
        employee_id: raw.employee_id,
        email: raw.email,
        role: (raw.role === 'employee' || raw.role === 'staff') ? 'junior_staff' : raw.role,
        department_name: raw.department?.name || raw.department_name || (typeof raw.department === 'string' ? raw.department : undefined),
        hire_date: raw.hire_date,
        first_name: raw.first_name,
        last_name: raw.last_name,
        // grade removed
      };
      console.log('[StaffManagement] Normalized profile response:', normalized);
      setProfileModal({ open: true, loading: false, employee: emp, data: normalized, error: null });
      setSelectedRole(normalized.role || 'junior_staff');
      // Initialize editable fields
      setProfileEditFields({ 
        employee_id: normalized.employee_id || '', 
        hire_date: normalized.hire_date || '',
        new_email: '',
        new_password: ''
      });
    } catch (e) {
      const status = e.response?.status;
      const msg = e.response?.data?.detail || e.response?.data?.error || 'Failed to load profile';
      console.error('[StaffManagement] Failed to load profile', { status, error: e, response: e.response?.data });
      setProfileModal({ open: true, loading: false, employee: emp, data: null, error: msg });
      showToast({ type: 'error', message: msg });
    }
  };

  const toggleDepartment = (deptId) => {
    setExpandedDepts((prev) => ({
      ...prev,
      [deptId]: !prev[deptId],
    }));
  };



  const getRoleBadge = (role) => {
    // Normalize legacy aliases to current role codes for display
    if (role === 'staff' || role === 'employee') {
      role = 'junior_staff';
    } else if (role === 'hod') {
      role = 'manager';
    }
    const roleColors = {
      junior_staff: 'bg-gray-100 text-gray-800',
      senior_staff: 'bg-slate-100 text-slate-800',
      manager: 'bg-blue-100 text-blue-800',
      hr: 'bg-green-100 text-green-800',
      ceo: 'bg-indigo-100 text-indigo-800',
      admin: 'bg-purple-100 text-purple-800',
      employee: 'bg-gray-100 text-gray-800',
    };

    // Map role to display name (manager -> HOD)
    const roleDisplayMap = {
      junior_staff: 'Junior Staff',
      senior_staff: 'Senior Staff', 
      manager: 'HOD',
      hr: 'HR',
      admin: 'Admin',
      ceo: 'CEO',
      employee: 'Junior Staff',
    };

    const displayName = roleDisplayMap[role] || role?.replace('_', ' ')?.replace(/\b\w/g, l => l.toUpperCase()) || 'Staff';
    
    return (
      <span
        className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
          roleColors[role] || roleColors.junior_staff
        }`}
      >
        {displayName}
      </span>
    );
  };

  const filteredEmployees = useMemo(() => {
    const q = employeeQuery.trim().toLowerCase();
    if (!q) return employees;
    return employees.filter(
      (e) =>
        e.name?.toLowerCase().includes(q) ||
        e.email?.toLowerCase().includes(q) ||
        e.department?.toLowerCase().includes(q) ||
        e.employee_id?.toLowerCase().includes(q)
    );
  }, [employeeQuery, employees]);

  const [selectedRole, setSelectedRole] = useState('');

  const handleRoleChange = (newRole) => {
    setSelectedRole(newRole);
  };

  const saveProfileRole = async () => {
    if (!profileModal?.employee?.id || !selectedRole) return;
    const currentRole = profileModal?.data?.role || 'junior_staff';
    if (currentRole === selectedRole) return; // no change
    try {
      setProfileRoleSaving(true);
      const res = await api.patch(`/users/${profileModal.employee.id}/`, { role: selectedRole });
      const updatedUser = res.data || {};
      showToast({ type: 'success', message: 'Role updated' });
      // Update local modal data
      setProfileModal(prev => ({ ...prev, data: prev.data ? { ...prev.data, role: updatedUser.role } : prev.data }));
      const employeeId = profileModal.employee.id;
      setEmployees(prev => prev.map((emp) => (
        emp.id === employeeId
          ? { ...emp, role: updatedUser.role }
          : emp
      )));
      setDepartments(prev => prev.map((dept) => {
        if (!Array.isArray(dept.staff)) {
          return dept;
        }
        return {
          ...dept,
          staff: dept.staff.map((staffer) => (
            staffer.id === employeeId
              ? { ...staffer, role: updatedUser.role }
              : staffer
          )),
        };
      }));
    } catch (e) {
      const msg = e.response?.data?.detail || e.response?.data?.error || 'Failed to update role';
      showToast({ type: 'error', message: msg });
    } finally {
      setProfileRoleSaving(false);
    }
  };

  const saveProfileFields = async () => {
    if (!profileModal?.employee?.id) return;
    const currentData = profileModal.data || {};
    const updates = {};
    
    // Check if employee_id changed
    if (profileEditFields.employee_id !== (currentData.employee_id || '')) {
      const trimmedEmployeeId = profileEditFields.employee_id.trim();
      if (!trimmedEmployeeId) {
        showToast({ type: 'error', message: 'Employee ID is required' });
        return;
      }
      updates.employee_id = trimmedEmployeeId;
    }
    
    // Check if hire_date changed
    if (profileEditFields.hire_date !== (currentData.hire_date || '')) {
      updates.hire_date = profileEditFields.hire_date;
    }
    
    // If no changes, return early
    if (Object.keys(updates).length === 0) return;
    
    try {
      setProfileFieldsSaving(true);
      const res = await api.patch(`/users/${profileModal.employee.id}/`, updates);
      const updatedUser = res.data || {};
      showToast({ type: 'success', message: 'Profile updated successfully' });
      
      // Update local modal data
      setProfileModal(prev => ({ 
        ...prev, 
        data: prev.data ? { 
          ...prev.data, 
          employee_id: updatedUser.employee_id,
          hire_date: updatedUser.hire_date 
        } : prev.data 
      }));
      
      // Update the edit fields to match saved data (preserve new_email and new_password)
      setProfileEditFields(prev => ({
        ...prev,
        employee_id: updatedUser.employee_id || '',
        hire_date: updatedUser.hire_date || ''
      }));
      
      // Update employees list
      const employeeId = profileModal.employee.id;
      setEmployees(prev => prev.map((emp) => (
        emp.id === employeeId
          ? { ...emp, employee_id: updatedUser.employee_id, hire_date: updatedUser.hire_date }
          : emp
      )));
      
      // Update departments list
      setDepartments(prev => prev.map((dept) => {
        if (!Array.isArray(dept.staff)) {
          return dept;
        }
        return {
          ...dept,
          staff: dept.staff.map((staffer) => (
            staffer.id === employeeId
              ? { ...staffer, employee_id: updatedUser.employee_id, hire_date: updatedUser.hire_date }
              : staffer
          )),
        };
      }));
    } catch (e) {
      console.error('Profile update error:', e.response?.data);
      let msg = 'Failed to update profile';
      
      // Handle specific validation errors
      if (e.response?.data?.employee_id) {
        if (Array.isArray(e.response.data.employee_id)) {
          msg = e.response.data.employee_id.join(', ');
        } else {
          msg = e.response.data.employee_id;
        }
      } else {
        msg = e.response?.data?.detail || e.response?.data?.error || msg;
      }
      
      showToast({ type: 'error', message: msg });
    } finally {
      setProfileFieldsSaving(false);
    }
  };

  const resetEmployeePassword = async () => {
    if (!profileModal?.employee?.id) return;
    const newPassword = profileEditFields.new_password.trim();
    
    if (!newPassword) {
      showToast({ type: 'error', message: 'New password is required' });
      return;
    }
    
    if (newPassword.length < 8) {
      showToast({ type: 'error', message: 'Password must be at least 8 characters' });
      return;
    }
    
    try {
      setResetPasswordSaving(true);
      await api.post(`/users/${profileModal.employee.id}/reset-password/`, { 
        new_password: newPassword 
      });
      showToast({ type: 'success', message: 'Password reset successfully' });
      setProfileEditFields(prev => ({ ...prev, new_password: '' }));
    } catch (e) {
      console.error('Password reset error:', e.response?.data);
      const msg = e.response?.data?.error || e.response?.data?.detail || 'Failed to reset password';
      showToast({ type: 'error', message: msg });
    } finally {
      setResetPasswordSaving(false);
    }
  };

  const updateEmployeeEmail = async () => {
    if (!profileModal?.employee?.id) return;
    const newEmail = profileEditFields.new_email.trim();
    
    if (!newEmail) {
      showToast({ type: 'error', message: 'New email is required' });
      return;
    }
    
    if (!newEmail.includes('@')) {
      showToast({ type: 'error', message: 'Invalid email format' });
      return;
    }
    
    try {
      setUpdateEmailSaving(true);
      const res = await api.patch(`/users/${profileModal.employee.id}/update-email/`, { 
        email: newEmail 
      });
      showToast({ type: 'success', message: 'Email updated successfully' });
      
      // Update modal data
      setProfileModal(prev => ({ 
        ...prev, 
        data: prev.data ? { ...prev.data, email: res.data.new_email } : prev.data 
      }));
      
      // Update employees list
      const employeeId = profileModal.employee.id;
      setEmployees(prev => prev.map((emp) => (
        emp.id === employeeId ? { ...emp, email: res.data.new_email } : emp
      )));
      
      // Clear the input
      setProfileEditFields(prev => ({ ...prev, new_email: '' }));
    } catch (e) {
      console.error('Email update error:', e.response?.data);
      const msg = e.response?.data?.error || e.response?.data?.detail || 'Failed to update email';
      showToast({ type: 'error', message: msg });
    } finally {
      setUpdateEmailSaving(false);
    }
  };

  const openBenefits = async (emp) => {
    try {
      setBenefitsModal({ open: true, loading: true, employee: emp, rows: [] });
      const res = await api.get(`/leaves/balances/employee/${emp.id}/current_year/`);
      const items = res.data?.items || [];
      const rows = items.map((it) => ({
        leave_type: it.leave_type.id,
        leave_type_name: it.leave_type.name,
        entitled_days: String(it.entitled_days ?? 0),
      }));
      setBenefitsModal({ open: true, loading: false, employee: emp, rows });
    } catch (e) {
      setBenefitsModal({ open: false, loading: false, employee: null, rows: [] });
      const msg = e.response?.data?.detail || 'Failed to load benefits';
      showToast({ type: 'error', message: msg });
    }
  };

  const openLeaveHistory = async (emp) => {
    if (!emp || !emp.id) {
      showToast({ type: 'error', message: 'Invalid employee record – missing ID' });
      console.error('openLeaveHistory called with invalid employee object:', emp);
      return;
    }
    console.log('[StaffManagement] Opening leave history for employee:', emp);
    setLeaveHistoryModal({ open: true, loading: true, employee: emp, requests: [], searchQuery: '' });
    try {
      // Use the HOD endpoint to get all leave requests for this employee
      const res = await api.get(`/leaves/manager/?employee=${emp.id}&ordering=-created_at`);
      const requests = res.data?.results || res.data || [];
      console.log('[StaffManagement] Leave history response:', requests);
      setLeaveHistoryModal({ open: true, loading: false, employee: emp, requests, searchQuery: '' });
    } catch (e) {
      const status = e.response?.status;
      const msg = e.response?.data?.detail || e.response?.data?.error || 'Failed to load leave history';
      console.error('[StaffManagement] Failed to load leave history', { status, error: e, response: e.response?.data });
      setLeaveHistoryModal({ open: true, loading: false, employee: emp, requests: [], searchQuery: '' });
      showToast({ type: 'error', message: msg });
    }
  };

  // Filter leave history requests based on search query
  const filteredLeaveHistory = useMemo(() => {
    const query = leaveHistoryModal.searchQuery?.trim().toLowerCase();
    if (!query) return leaveHistoryModal.requests;
    
    return leaveHistoryModal.requests.filter(request => 
      request.leave_type_name?.toLowerCase().includes(query) ||
      request.leave_type?.name?.toLowerCase().includes(query) ||
      request.reason?.toLowerCase().includes(query) ||
      request.status?.toLowerCase().includes(query) ||
      request.approval_comments?.toLowerCase().includes(query) ||
      request.start_date?.includes(query) ||
      request.end_date?.includes(query)
    );
  }, [leaveHistoryModal.requests, leaveHistoryModal.searchQuery]);

  const saveBenefits = async () => {
    const { employee, rows } = benefitsModal;
    // Validate
    const payload = {
      items: rows.map((r) => ({ leave_type: r.leave_type, entitled_days: parseInt(r.entitled_days, 10) || 0 })),
    };
    if (payload.items.some((i) => i.entitled_days < 0)) {
      showToast({ type: 'warning', message: 'Entitled days must be non-negative' });
      return;
    }
    try {
      setBenefitsModal((prev) => ({ ...prev, loading: true }));
      const res = await api.post(`/leaves/balances/employee/${employee.id}/set_entitlements/`, payload);
      const errs = res.data?.errors || [];
      if (errs.length) {
        showToast({ type: 'warning', message: `Saved with ${errs.length} warnings` });
      } else {
        showToast({ type: 'success', message: 'Benefits saved' });
      }
      setBenefitsModal({ open: false, loading: false, employee: null, rows: [] });
    } catch (e) {
      const msg = e.response?.data?.detail || e.response?.data?.error || 'Failed to save benefits';
      showToast({ type: 'error', message: msg });
      setBenefitsModal((prev) => ({ ...prev, loading: false }));
    }
  };

  const openNewDepartmentModal = () => {
    setNewDepartmentModal({ open: true, loading: false, name: '', description: '' });
  };

  const openNewAffiliateModal = () => {
    setNewAffiliateModal({ open: true, loading: false, name: '', description: '' });
  };

  const createDepartment = async () => {
    const { name, description } = newDepartmentModal;
    if (!name.trim()) {
      showToast({ type: 'warning', message: 'Department name is required' });
      return;
    }
    
    try {
      setNewDepartmentModal((prev) => ({ ...prev, loading: true }));
      await api.post('/users/departments/', { name: name.trim(), description: description.trim() });
      showToast({ type: 'success', message: `Department "${name}" created successfully` });
      setNewDepartmentModal({ open: false, loading: false, name: '', description: '' });
      fetchStaffData(); // Refresh the data
    } catch (error) {
      const msg = error.response?.data?.name?.[0] || error.response?.data?.detail || 'Failed to create department';
      showToast({ type: 'error', message: msg });
      setNewDepartmentModal((prev) => ({ ...prev, loading: false }));
    }
  };

  const createAffiliate = async () => {
    const { name, description } = newAffiliateModal;
    if (!name.trim()) {
      showToast({ type: 'warning', message: 'Affiliate name is required' });
      return;
    }
    try {
      setNewAffiliateModal((prev) => ({ ...prev, loading: true }));
      const payload = { name: name.trim() };
      if (description && description.trim()) payload.description = description.trim();
      const res = await api.post('/users/affiliates/', payload);
      showToast({ type: 'success', message: `Affiliate "${res.data?.name || name}" created successfully` });
      setNewAffiliateModal({ open: false, loading: false, name: '', description: '' });
      // Refresh list
      fetchAffiliates();
    } catch (error) {
      const msg = error.response?.data?.name?.[0] || error.response?.data?.detail || 'Failed to create affiliate';
      showToast({ type: 'error', message: msg });
      setNewAffiliateModal((prev) => ({ ...prev, loading: false }));
    }
  };

  const openNewEmployeeModal = () => {
    setNewEmployeeModal({
      open: true, 
      loading: false, 
      username: '', 
      email: '', 
      first_name: '', 
      last_name: '', 
      employee_id: '', 
      role: 'junior_staff', 
      affiliate_id: '',
      department_id: '', 
      password: '',
      hire_date: ''
    });
  };

  const createEmployee = async () => {
    const { username, email, first_name, last_name, employee_id, role, affiliate_id, department_id, password, hire_date } = newEmployeeModal;
    
    // Updated validation: email, first_name, last_name are required
    if (!email.trim() || !first_name.trim() || !last_name.trim() || !role) {
      showToast({ type: 'warning', message: 'Email, first name, last name, and role are required' });
      return;
    }
    
    // Validate affiliate selection
    if (!affiliate_id) {
      showToast({ type: 'warning', message: 'Please select an affiliate' });
      return;
    }
    
    // If Merban Capital selected, department is required
    const selectedAffiliate = affiliates.find(a => a.id === parseInt(affiliate_id));
    if (selectedAffiliate && selectedAffiliate.name === 'MERBAN CAPITAL' && !department_id) {
      showToast({ type: 'warning', message: 'Department is required for Merban Capital employees' });
      return;
    }
    
    try {
      setNewEmployeeModal((prev) => ({ ...prev, loading: true }));
      const data = {
        email: email.trim(),
        first_name: first_name.trim(),
        last_name: last_name.trim(),
        role,
        affiliate_id: parseInt(affiliate_id),
        is_active_employee: true
      };
      
      // Optional fields
      if (username.trim()) {
        data.username = username.trim();
      }
      
      if (employee_id.trim()) {
        data.employee_id = employee_id.trim();
      }
      
      if (department_id) {
        data.department_id = parseInt(department_id, 10);
      }
      
      if (password.trim()) {
        data.password = password.trim();
      }
      
      if (hire_date) {
        data.hire_date = hire_date;
      }
      
      await api.post('/users/staff/', data);
      showToast({ type: 'success', message: `Employee "${first_name} ${last_name}" created successfully` });
      setNewEmployeeModal({
        open: false, 
        loading: false, 
        username: '', 
        email: '', 
        first_name: '', 
        last_name: '', 
        employee_id: '', 
        role: 'junior_staff',
        affiliate_id: '', 
        department_id: '', 
        password: '',
        hire_date: ''
      });
      fetchStaffData(); // Refresh the data
    } catch (error) {
      const msg = error.response?.data?.username?.[0] || 
                  error.response?.data?.email?.[0] || 
                  error.response?.data?.employee_id?.[0] ||
                  error.response?.data?.detail || 
                  'Failed to create employee';
      showToast({ type: 'error', message: msg });
      setNewEmployeeModal((prev) => ({ ...prev, loading: false }));
    }
  };

  const openHodModal = (department) => {
    setHodModal({
      open: true,
      loading: false,
      department,
      selectedManagerId: department.manager?.id || ''
    });
  };

  const updateDepartmentHod = async () => {
    setHodModal(prev => ({ ...prev, loading: true }));
    try {
      await api.post(`/users/departments/${hodModal.department.id}/set_manager/`, {
        manager_id: hodModal.selectedManagerId || null
      });
      
      showToast({ 
        type: 'success', 
        message: `Department HOD ${hodModal.selectedManagerId ? 'updated' : 'removed'} successfully!` 
      });
      setHodModal({ open: false, loading: false, department: null, selectedManagerId: '' });
      fetchStaffData();
    } catch (error) {
      console.error('Error updating HOD:', error);
      showToast({ 
        type: 'error', 
        message: error.response?.data?.error || 'Failed to update department HOD' 
      });
    } finally {
      setHodModal(prev => ({ ...prev, loading: false }));
    }
  };

  const handleImportFile = async (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = async (ev) => {
      try {
        const text = ev.target.result;
        const rows = text.split(/\r?\n/).filter(Boolean);
        if (!rows.length) {
          showToast({ type: 'warning', message: 'Empty CSV file.' });
          return;
        }
        const header = rows
          .shift()
          .split(',')
          .map((h) => h.trim().toLowerCase());
        
        // Enhanced field mapping
    const nameIdx = header.indexOf('name');
    const emailIdx = header.indexOf('email');
    const affiliateIdx = header.indexOf('affiliate');
    const deptIdx = header.indexOf('department');
        const roleIdx = header.indexOf('role');
        const employeeIdIdx = header.indexOf('employee_id');
        const hireDateIdx = header.indexOf('hire_date');
        
        // Validate required fields
        if (nameIdx === -1 || emailIdx === -1) {
          showToast({ type: 'error', message: 'CSV must contain at least "name" and "email" columns' });
          return;
        }
        
        if (affiliateIdx === -1) {
          showToast({ type: 'error', message: 'CSV must contain "affiliate" column' });
          return;
        }
        
  const validRoles = ['junior_staff', 'senior_staff', 'manager', 'hr', 'ceo', 'admin'];
        
        const parsed = rows.map((r, i) => {
          const cols = r.split(',').map((c) => c.trim());
          
          // Extract affiliate
          const affiliateName = cols[affiliateIdx] || '';
          const matchedAffiliate = affiliates.find(a => (a.name || '').toLowerCase() === affiliateName.toLowerCase());
          
          if (!matchedAffiliate) {
            return { error: `Row ${i + 2}: Invalid or missing affiliate "${affiliateName}"` };
          }
          
          // Extract and validate role
          const role = cols[roleIdx] || 'junior_staff';
          const validatedRole = validRoles.includes(role) ? role : 'junior_staff';
          
          // Extract employee ID or generate one
          const employeeId = cols[employeeIdIdx] || `EMP${String(Date.now() + i).substring(-6)}`;
          
          // Extract hire date or use current date
          const hireDate = cols[hireDateIdx] || new Date().toISOString().split('T')[0];
          
          // Split name into first and last name
          const fullName = cols[nameIdx] || '';
          const nameParts = fullName.trim().split(' ');
          const firstName = nameParts[0] || '';
          const lastName = nameParts.slice(1).join(' ') || '';
          
          // Generate username from email
          const email = cols[emailIdx] || '';
          const username = email.split('@')[0] || `user${Date.now() + i}`;
          
          // Handle department based on affiliate
          let department_id = null;
          const deptName = cols[deptIdx] || '';
          
          // For Merban Capital, department is required
          if (matchedAffiliate.name === 'Merban Capital') {
            if (!deptName) {
              return { error: `Row ${i + 2}: Department required for Merban Capital employees` };
            }
            const matchedDept = departments.find(d => (d.name || '').toLowerCase() === deptName.toLowerCase());
            if (!matchedDept) {
              return { error: `Row ${i + 2}: Invalid department "${deptName}"` };
            }
            department_id = matchedDept.id;
          }
          // For SDSL/SBL, users remain as individual entities (no department assignment)
          
          return {
            username,
            email,
            first_name: firstName,
            last_name: lastName,
            employee_id: employeeId,
            role: validatedRole,
            hire_date: hireDate,
            affiliate_id: matchedAffiliate.id,
            department_id: department_id,
            password: 'TempPass123!', // Default temporary password
            is_active_employee: true
          };
        });
        
        // Filter out errors and collect valid entries
        const validEntries = parsed.filter(p => !p.error);
        const parseErrors = parsed.filter(p => p.error);
        
        if (parseErrors.length > 0) {
          console.error('CSV parsing errors:', parseErrors);
          showToast({ 
            type: 'warning', 
            message: `${parseErrors.length} rows have errors. Check console for details.` 
          });
        }
        
        if (validEntries.length === 0) {
          showToast({ type: 'error', message: 'No valid employees to import' });
          return;
        }
        
        // Show preview and ask for confirmation
        showToast({ type: 'info', message: `Parsed ${validEntries.length} valid employees. Starting import...` });
        
        // Import employees one by one to the backend
        let successCount = 0;
        let errorCount = 0;
        const errors = [];
        
        for (let i = 0; i < validEntries.length; i++) {
          const employeeData = validEntries[i];
          try {
            const response = await api.post('/users/staff/', employeeData);
            successCount++;
            console.log(`Successfully imported employee ${i + 1}:`, response.data);
          } catch (error) {
            errorCount++;
            const errorMsg = error.response?.data?.detail || 
                           error.response?.data?.email?.[0] || 
                           error.response?.data?.employee_id?.[0] || 
                           'Unknown error';
            errors.push(`Row ${i + 1} (${employeeData.email}): ${errorMsg}`);
            console.error(`Failed to import employee ${i + 1}:`, error.response?.data);
          }
        }
        
        // Show results
        if (successCount > 0) {
          showToast({ 
            type: 'success', 
            message: `Successfully imported ${successCount} employees to the system!` 
          });
          // Refresh the staff data
          fetchStaffData();
        }
        
        if (errorCount > 0) {
          showToast({ 
            type: 'warning', 
            message: `${errorCount} employees failed to import. Check console for details.` 
          });
          console.error('Import errors:', errors);
        }
        
      } catch (err) {
        console.error('Import error:', err);
        showToast({ type: 'error', message: 'Failed to process CSV. Please check the file format.' });
      } finally {
        if (fileInputRef.current) fileInputRef.current.value = null;
      }
    };
    reader.readAsText(f);
  };

  const handleExportCSV = () => {
    const csv = [
      'name,email,department,employee_id,role',
      ...employees.map(
        (e) => `${e.name || ''},${e.email || ''},${e.department || ''},${e.employee_id || ''},${e.role || ''}`
      ),
    ].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'employees.csv';
    a.click();
    URL.revokeObjectURL(url);
    showToast({ type: 'info', message: 'Exported current employees as CSV' });
  };

  const downloadTemplateCSV = () => {
  const csv = `name,email,affiliate,department,role,employee_id,hire_date
John Doe,john.doe@company.com,Merban Capital,IT,senior_staff,EMP001,2023-01-15
Jane Smith,jane.smith@company.com,Merban Capital,HR & Admin,hod,HOD001,2022-03-01
Alice Johnson,alice.johnson@company.com,SDSL,,junior_staff,EMP002,2024-06-10
Bob Wilson,bob.wilson@company.com,SBL,,senior_staff,EMP003,2023-08-22`;
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'employees_template.csv';
    a.click();
    URL.revokeObjectURL(url);
    showToast({ type: 'info', message: 'Downloaded CSV template with affiliate column' });
  };

  const handleSidebarKeyDown = (e) => {
    const idx = SIDEBAR_ITEMS.findIndex((s) => s.id === active);
    if (e.key === 'ArrowDown') {
      const next = SIDEBAR_ITEMS[(idx + 1) % SIDEBAR_ITEMS.length];
      setActive(next.id);
    } else if (e.key === 'ArrowUp') {
      const prev = SIDEBAR_ITEMS[(idx - 1 + SIDEBAR_ITEMS.length) % SIDEBAR_ITEMS.length];
      setActive(prev.id);
    }
  };

  // Prevent unauthorized direct navigation (e.g., stale state or manual set)
  useEffect(() => {
    if (active === 'role-management' && !canManageGradeEntitlements) {
      setActive('leave-policies');
    }
  }, [active, canManageGradeEntitlements]);

  const openLeaveTypeModal = async (lt) => {
    try {
      setLeaveTypeModal({ open: true, name: lt.name, id: lt.id, value: '', loading: false });
      // Prefill using backend summary
      const res = await api.get(`/leaves/types/${lt.id}/entitlement_summary/`);
      const v = res.data?.common_entitled_days ?? '';
      setLeaveTypeModal((prev) => ({ ...prev, value: String(v) }));
    } catch (e) {
      // If summary fails, just leave blank
    }
  };

  const saveLeaveTypeEntitlement = async () => {
    const { id, value } = leaveTypeModal;
    const days = parseInt(value, 10);
    if (isNaN(days) || days < 0) {
      showToast({ type: 'warning', message: 'Please enter a valid non-negative number of days.' });
      return;
    }
    try {
      setLeaveTypeModal((prev) => ({ ...prev, loading: true }));
      const res = await api.post(`/leaves/types/${id}/set_entitlement/`, { entitled_days: days });
      showToast({ type: 'success', message: `Saved: ${res.data.entitled_days} days for ${res.data.leave_type}` });
      setLeaveTypeModal({ open: false, name: '', id: null, value: '', loading: false });
    } catch (error) {
      const msg = error.response?.data?.detail || error.response?.data?.error || 'Failed to save entitlement';
      showToast({ type: 'error', message: msg });
      setLeaveTypeModal((prev) => ({ ...prev, loading: false }));
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-2 border-sky-500 border-t-transparent"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6">
      <div className="max-w-7xl mx-auto flex gap-6">
        {/* Sidebar */}
        <nav
          className="w-64 hidden md:block"
          aria-label="Staff navigation"
          onKeyDown={handleSidebarKeyDown}
        >
          <div className="bg-white rounded-md shadow divide-y">
            {SIDEBAR_ITEMS.map((item) => {
              const isActive = item.id === active;
              const activeClass = isActive ? 'bg-sky-50 border-sky-500 text-sky-700' : 'hover:bg-gray-50';
              return (
                <button
                  key={item.id}
                  onClick={() => setActive(item.id)}
                  className={`w-full text-left px-4 py-3 flex items-center justify-between gap-3 border-b ${activeClass}`}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <span className="font-medium">{item.label}</span>
                  <span className="text-xs text-gray-400">
                    {item.id === 'employees' ? employees.length : ''}
                  </span>
                </button>
              );
            })}
          </div>
        </nav>

        {/* Content */}
        <main className="flex-1">
          <div className="mb-4 flex items-center justify-between">
            <h1 className="text-2xl font-semibold">Staff</h1>
            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  console.log('🔄 Manual refresh triggered');
                  fetchStaffData();
                }}
                className="px-3 py-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
              >
                Refresh
              </button>
              {active === 'departments' && (
                <button
                  onClick={openNewDepartmentModal}
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                >
                  New department
                </button>
              )}
              {/* New employee creation moved to affiliate pages (MERBAN, SDSL, SBL). */}
              {active === 'employees' && (
                <button
                  onClick={() => setDeleteEmployeeModal({ open: true, selected: {}, processing: false })}
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-red-600 text-red-600"
                >
                  Delete employees
                </button>
              )}
              {active === 'affiliates' && canManageGradeEntitlements && (
                <button
                  onClick={openNewAffiliateModal}
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                >
                  New affiliate
                </button>
              )}
              {active === 'affiliates' && canManageGradeEntitlements && (
                <button
                  onClick={() => setDeleteAffiliateModal({ open: true, selected: {}, processing: false })}
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-red-600 text-red-600"
                >
                  Delete affiliates
                </button>
              )}
            </div>
          </div>

          <div className="bg-white shadow rounded-md p-4 sm:p-6">
            {active === 'affiliates' && (
              <section>
                <h2 className="text-lg font-medium mb-4">Affiliates</h2>
                <p className="text-sm text-gray-600 mb-4">Click an affiliate to manage its departments.</p>
                {affiliates.length === 0 ? (
                  <div className="text-sm text-gray-500">No affiliates yet.</div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {affiliates.map((aff) => (
                      <button
                        key={aff.id}
                        onClick={() => navigate(`/staff/affiliates/${aff.id}`)}
                        className="text-left border border-gray-200 rounded-lg p-4 bg-white hover:bg-gray-50 focus:outline-none"
                      >
                        <h3 className="text-base font-semibold text-gray-900">{aff.name}</h3>
                        <div className="mt-2 space-y-1 text-sm text-gray-600">
                              <p>Affiliate</p>
                              <p><span className="text-gray-700 font-medium">CEO:</span> {affiliateInfo[aff.id]?.ceo || '—'}</p>
                              {aff.name === 'MERBAN CAPITAL' && (
                                <p><span className="text-gray-700 font-medium">Departments:</span> {affiliateInfo[aff.id]?.depts ?? '—'}</p>
                              )}
                              <p><span className="text-gray-700 font-medium">Members:</span> {affiliateInfo[aff.id]?.members ?? '—'}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </section>
            )}
            {active === 'departments' && (
              <section>
                <h2 className="text-lg font-medium mb-4">Departments</h2>
                {departments.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {departments.map((dept) => (
                      <div key={dept.id} className="border border-gray-200 rounded-lg overflow-hidden bg-white">
                        <button
                          onClick={() => toggleDepartment(dept.id)}
                          className="w-full px-4 py-4 text-left hover:bg-gray-50 focus:outline-none focus:bg-gray-50 transition-colors"
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <h4 className="text-lg font-medium text-gray-900">{dept.name}</h4>
                              {dept.description && (
                                <p className="text-sm text-gray-500 mt-1">{dept.description}</p>
                              )}
                              <p className="text-sm text-gray-600 mt-1">
                                {dept.staff_count} staff member{dept.staff_count !== 1 ? 's' : ''}
                              </p>
                              {dept.manager ? (
                                <p className="text-sm text-blue-600 mt-1">
                                  <span className="font-medium">HOD:</span> {dept.manager.name} ({dept.manager.employee_id})
                                </p>
                              ) : (
                                <p className="text-sm text-amber-600 mt-1">
                                  <span className="font-medium">⚠️ No HOD assigned</span>
                                </p>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  openHodModal(dept);
                                }}
                                className="px-3 py-1 text-xs font-medium rounded-md border border-blue-200 text-blue-700 hover:bg-blue-50"
                              >
                                Set HOD
                              </button>
                              <div className="flex-shrink-0">
                                <svg
                                  className={`h-5 w-5 text-gray-400 transform transition-transform ${
                                    expandedDepts[dept.id] ? 'rotate-90' : ''
                                  }`}
                                  viewBox="0 0 20 20"
                                  fill="currentColor"
                                >
                                  <path
                                    fillRule="evenodd"
                                    d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                                    clipRule="evenodd"
                                  />
                                </svg>
                              </div>
                            </div>
                          </div>
                        </button>

                        {expandedDepts[dept.id] && (
                          <div className="px-4 pb-4">
                            {dept.staff.length > 0 ? (
                              <div className="space-y-3">
                                {dept.staff.map((staff) => (
                                  <div key={staff.id} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                                    <div className="flex items-start justify-between">
                                      <div className="flex-1">
                                        <div className="flex items-center gap-3">
                                          <h5 className="text-sm font-semibold text-gray-900">{cleanName(staff.name)}</h5>
                                          {getRoleBadge(staff.role)}
                                        </div>
                                        <div className="mt-2 space-y-1">
                                          <p className="text-sm text-gray-600">
                                            <span className="font-medium">Employee ID:</span> {staff.employee_id}
                                          </p>
                                          <p className="text-sm text-gray-600">
                                            <span className="font-medium">Email:</span> {staff.email}
                                          </p>
                                          {staff.hire_date && (
                                            <p className="text-sm text-gray-600">
                                              <span className="font-medium">Hire Date:</span>{' '}
                                              {new Date(staff.hire_date).toLocaleDateString()}
                                            </p>
                                          )}
                                          {staff.manager && (
                                            <p className="text-sm text-gray-600">
                                              <span className="font-medium">Approver:</span>{' '}
                                              {cleanName(staff.manager.name)} ({staff.manager.employee_id})
                                            </p>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <div className="text-sm text-gray-500 italic">No staff members in this department.</div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-8 text-center text-gray-500">No departments found.</div>
                )}
              </section>
            )}

            {active === 'employees' && (
              <section>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-medium">Employees</h2>
                  <div className="flex items-center gap-2">
                    <input
                      type="search"
                      value={employeeQuery}
                      onChange={(e) => setEmployeeQuery(e.target.value)}
                      placeholder="Search by name, email, dept or ID"
                      className="border px-3 py-2 rounded-md"
                      aria-label="Search employees"
                    />
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm text-left">
                    <thead className="text-xs uppercase text-gray-500">
                      <tr>
                        <th className="px-3 py-2">Name</th>
                        <th className="px-3 py-2">Email</th>
                        <th className="px-3 py-2">Department</th>
                        <th className="px-3 py-2">Employee ID</th>
                        <th className="px-3 py-2">Role</th>
                        <th className="px-3 py-2">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredEmployees.map((emp) => (
                        <tr key={emp.id} className="border-t">
                          <td className="px-3 py-2">{emp.name}</td>
                          <td className="px-3 py-2">{emp.email}</td>
                          <td className="px-3 py-2">{emp.role === 'ceo' ? '—' : (emp.department || '—')}</td>
                          <td className="px-3 py-2">{emp.employee_id}</td>
                          <td className="px-3 py-2">{getRoleBadge(emp.role)}</td>
                          <td className="px-3 py-2">
                            <div className="flex flex-wrap gap-2">
                              <button
                                onClick={() => openProfile(emp)}
                                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                              >
                                Profile
                              </button>
                              <button
                                onClick={() => openBenefits(emp)}
                                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                              >
                                Set benefits
                              </button>
                              <button
                                onClick={() => openLeaveHistory(emp)}
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
              </section>
            )}

            {/* Affiliates section removed */}

            {active === 'leave-types' && (
              <section>
                <h2 className="text-lg font-medium mb-4">Leave Types</h2>
                <LeaveTypesList onConfigure={openLeaveTypeModal} />
              </section>
            )}

            {active === 'leave-policies' && (
              <section>
                <h2 className="text-lg font-medium mb-4">Leave Policies</h2>
                <p className="text-sm text-gray-600 mb-4">Create rules and entitlements (carryover, blackout dates, max continuous days)</p>
                {canManageGradeEntitlements && (
                  <div className="mb-6">
                    <button
                      onClick={() => setActive('role-management')}
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium border border-sky-600 text-white bg-sky-600 hover:bg-sky-700"
                    >
                      Manage Roles
                    </button>
                    <p className="mt-2 text-xs text-gray-500 max-w-md">Set role-based leave entitlements and manage employee classifications.</p>
                  </div>
                )}
                <div className="space-y-3">
                  <div className="p-3 bg-gray-50 rounded">Default annual allocation: <strong>20 days</strong></div>
                  <div className="p-3 bg-gray-50 rounded">Maternity: <strong>90 days</strong></div>
                </div>
              </section>
            )}

            {active === 'import' && (
              <section>
                <h2 className="text-lg font-medium mb-4">Import employees</h2>
                <p className="text-sm text-gray-600 mb-4">
                  Import employees using CSV format with enhanced fields:
                </p>
                <div className="bg-blue-50 border border-blue-200 rounded-md p-3 mb-4">
                  <h3 className="text-sm font-medium text-blue-900 mb-2">Supported CSV Columns:</h3>
                  <ul className="text-xs text-blue-800 space-y-1">
                    <li><strong>Required:</strong> name, email</li>
                    <li><strong>Optional:</strong> department, role, employee_id, hire_date</li>
                    <li><strong>Valid roles:</strong> junior_staff, senior_staff, manager, hr, ceo, admin</li>
                    <li><strong>Date format:</strong> YYYY-MM-DD (e.g., 2023-01-15)</li>
                  </ul>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <button
                    onClick={downloadTemplateCSV}
                    className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200 text-sky-700 hover:bg-sky-50"
                  >
                    📄 Download Enhanced Template (CSV)
                  </button>
                  <input ref={fileInputRef} type="file" accept="text/csv" onChange={handleImportFile} />
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  💡 The template includes sample data showing the correct format. 
                  Employees will be created in the system with temporary password "TempPass123!" (users should change on first login).
                </p>
              </section>
            )}

            {active === 'export' && (
              <section>
                <h2 className="text-lg font-medium mb-4">Export</h2>
                <p className="text-sm text-gray-600 mb-4">Export staff list as CSV for backups or HR systems.</p>
                <button
                  onClick={handleExportCSV}
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                >
                  Export CSV
                </button>
              </section>
            )}
            {active === 'role-management' && (
              <section>
                {canManageGradeEntitlements ? (
                  <RoleManagement />
                ) : (
                  <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-3">You are not authorized to view this section.</div>
                )}
              </section>
            )}
          </div>
        </main>
      </div>

      {/* Mobile bottom nav (simple) */}
      <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 md:hidden w-full max-w-md px-4">
        <div className="bg-white rounded-md shadow flex justify-between p-2">
          {SIDEBAR_ITEMS.map((it) => (
            <button
              key={it.id}
              onClick={() => setActive(it.id)}
              className={`flex-1 py-2 text-center ${it.id === active ? 'text-sky-600 font-semibold' : 'text-gray-600'}`}
            >
              {it.label}
            </button>
          ))}
        </div>
      </div>
      {leaveTypeModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
          <div className="bg-white rounded-md shadow p-6 w-full max-w-sm">
            <h3 className="text-lg font-semibold mb-2">Configure {leaveTypeModal.name}</h3>
            <p className="text-sm text-gray-600 mb-4">Set default annual entitlement for this leave type. This will apply to all active employees.</p>
            <label className="block text-sm font-medium text-gray-700 mb-1">Entitled days</label>
            <input
              type="number"
              min="0"
              value={leaveTypeModal.value}
              onChange={(e) => setLeaveTypeModal((prev) => ({ ...prev, value: e.target.value }))}
              className="w-full border rounded-md px-3 py-2 mb-4"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setLeaveTypeModal({ open: false, name: '', id: null, value: '', loading: false })}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                disabled={leaveTypeModal.loading}
              >
                Cancel
              </button>
              <button
                onClick={saveLeaveTypeEntitlement}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-sky-600 text-white bg-sky-600 hover:bg-sky-700"
                disabled={leaveTypeModal.loading}
              >
                {leaveTypeModal.loading ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

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
                {(() => { console.log('[StaffManagement] Rendering profile modal with data:', profileModal.data); return null; })()}
                
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
                
                {/* Department - Read only */}
                <div><span className="font-medium">Department:</span> {(profileModal.data.role === 'ceo' || /^executive(s)?$/i.test(profileModal.data.department_name || '')) ? '—' : (profileModal.data.department_name || '—')}</div>

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

      {/* New Department Modal */}
      {newDepartmentModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
          <div className="bg-white rounded-md shadow p-6 w-full max-w-sm">
            <h3 className="text-lg font-semibold mb-4">Create New Department</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Department Name *</label>
                <input
                  type="text"
                  value={newDepartmentModal.name}
                  onChange={(e) => setNewDepartmentModal((prev) => ({ ...prev, name: e.target.value }))}
                  className="w-full border rounded-md px-3 py-2"
                  placeholder="e.g. Engineering"
                  disabled={newDepartmentModal.loading}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={newDepartmentModal.description}
                  onChange={(e) => setNewDepartmentModal((prev) => ({ ...prev, description: e.target.value }))}
                  className="w-full border rounded-md px-3 py-2"
                  rows="3"
                  placeholder="Optional description"
                  disabled={newDepartmentModal.loading}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setNewDepartmentModal({ open: false, loading: false, name: '', description: '' })}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                disabled={newDepartmentModal.loading}
              >
                Cancel
              </button>
              <button
                onClick={createDepartment}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-blue-600 text-white bg-blue-600 hover:bg-blue-700"
                disabled={newDepartmentModal.loading}
              >
                {newDepartmentModal.loading ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Employee Modal */}
      {newEmployeeModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
          <div className="bg-white rounded-md shadow p-6 w-full max-w-lg">
            <h3 className="text-lg font-semibold mb-4">Create New Employee</h3>
            <div className="space-y-4 max-h-96 overflow-y-auto">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
                <input
                  type="email"
                  value={newEmployeeModal.email}
                  onChange={(e) => setNewEmployeeModal((prev) => ({ ...prev, email: e.target.value }))}
                  className="w-full border rounded-md px-3 py-2"
                  placeholder="john.doe@company.com"
                  disabled={newEmployeeModal.loading}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">First Name *</label>
                  <input
                    type="text"
                    value={newEmployeeModal.first_name}
                    onChange={(e) => setNewEmployeeModal((prev) => ({ ...prev, first_name: e.target.value }))}
                    className="w-full border rounded-md px-3 py-2"
                    placeholder="John"
                    disabled={newEmployeeModal.loading}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Last Name *</label>
                  <input
                    type="text"
                    value={newEmployeeModal.last_name}
                    onChange={(e) => setNewEmployeeModal((prev) => ({ ...prev, last_name: e.target.value }))}
                    className="w-full border rounded-md px-3 py-2"
                    placeholder="Doe"
                    disabled={newEmployeeModal.loading}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                  <input
                    type="text"
                    value={newEmployeeModal.username}
                    onChange={(e) => setNewEmployeeModal((prev) => ({ ...prev, username: e.target.value }))}
                    className="w-full border rounded-md px-3 py-2"
                    placeholder="john.doe (optional)"
                    disabled={newEmployeeModal.loading}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Employee ID</label>
                  <input
                    type="text"
                    value={newEmployeeModal.employee_id}
                    onChange={(e) => setNewEmployeeModal((prev) => ({ ...prev, employee_id: e.target.value }))}
                    className="w-full border rounded-md px-3 py-2"
                    placeholder="EMP001 (optional)"
                    disabled={newEmployeeModal.loading}
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Affiliate *</label>
                <select
                  value={newEmployeeModal.affiliate_id}
                  onChange={(e) => setNewEmployeeModal((prev) => ({ 
                    ...prev, 
                    affiliate_id: e.target.value,
                    // Clear department when affiliate changes
                    department_id: '' 
                  }))}
                  className="w-full border rounded-md px-3 py-2"
                  disabled={newEmployeeModal.loading}
                >
                  <option value="">Select Affiliate</option>
                  {affiliates.map((aff) => (
                    <option key={aff.id} value={aff.id}>{aff.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Department {(() => {
                    const selectedAffiliate = affiliates.find(a => a.id === parseInt(newEmployeeModal.affiliate_id));
                    return selectedAffiliate && selectedAffiliate.name === 'MERBAN CAPITAL' ? '*' : '';
                  })()}
                </label>
                <select
                  value={newEmployeeModal.department_id}
                  onChange={(e) => setNewEmployeeModal((prev) => ({ ...prev, department_id: e.target.value }))}
                  className="w-full border rounded-md px-3 py-2"
                  disabled={newEmployeeModal.loading || (() => {
                    const selectedAffiliate = affiliates.find(a => a.id === parseInt(newEmployeeModal.affiliate_id));
                    // Disable if SDSL or SBL selected, or if no affiliate selected
                    return !newEmployeeModal.affiliate_id || 
                           (selectedAffiliate && (selectedAffiliate.name === 'SDSL' || selectedAffiliate.name === 'SBL'));
                  })()}
                >
                  <option value="">
                    {(() => {
                      const selectedAffiliate = affiliates.find(a => a.id === parseInt(newEmployeeModal.affiliate_id));
                      if (!newEmployeeModal.affiliate_id) return 'Select affiliate first';
                      if (selectedAffiliate && (selectedAffiliate.name === 'SDSL' || selectedAffiliate.name === 'SBL')) {
                        return 'N/A for SDSL/SBL';
                      }
                      return 'Select Department';
                    })()}
                  </option>
                  {(() => {
                    const selectedAffiliate = affiliates.find(a => a.id === parseInt(newEmployeeModal.affiliate_id));
                    console.log('[Debug] Selected affiliate:', selectedAffiliate);
                    console.log('[Debug] All departments:', departments);
                    
                    if (selectedAffiliate && (selectedAffiliate.name === 'MERBAN CAPITAL' || selectedAffiliate.name === 'Merban Capital')) {
                      // Show departments linked to Merban affiliate, or all departments as fallback
                      const merbanDepts = departments.filter(dept => {
                        const isLinkedToMerban = dept.affiliate?.id === selectedAffiliate.id;
                        console.log(`[Debug] Department "${dept.name}" - affiliate: ${dept.affiliate?.name} (id: ${dept.affiliate?.id}), linked: ${isLinkedToMerban}`);
                        return isLinkedToMerban;
                      });
                      
                      // If no departments are linked to Merban, show all departments as fallback
                      const depsToShow = merbanDepts.length > 0 ? merbanDepts : departments;
                      console.log('[Debug] Departments to show:', depsToShow);
                      
                      if (merbanDepts.length === 0) {
                        console.log('[Debug] No departments linked to Merban - showing all departments as fallback');
                      }
                      
                      return depsToShow.map((dept) => (
                        <option key={dept.id} value={dept.id}>
                          {dept.name} {merbanDepts.length === 0 ? '(all)' : ''}
                        </option>
                      ));
                    }
                    return null;
                  })()}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Role *</label>
                  <select
                    value={newEmployeeModal.role}
                    onChange={(e) => setNewEmployeeModal((prev) => ({ ...prev, role: e.target.value }))}
                    className="w-full border rounded-md px-3 py-2"
                    disabled={newEmployeeModal.loading}
                  >
                    <option value="">Select Role</option>
                    <option value="junior_staff">Junior Staff</option>
                    <option value="senior_staff">Senior Staff</option>
                    <option value="manager">Head of Department</option>
                    <option value="hr">HR</option>
                    <option value="ceo">CEO</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Hire Date</label>
                  <input
                    type="date"
                    value={newEmployeeModal.hire_date}
                    onChange={(e) => setNewEmployeeModal((prev) => ({ ...prev, hire_date: e.target.value }))}
                    className="w-full border rounded-md px-3 py-2"
                    disabled={newEmployeeModal.loading}
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input
                  type="password"
                  value={newEmployeeModal.password}
                  onChange={(e) => setNewEmployeeModal((prev) => ({ ...prev, password: e.target.value }))}
                  className="w-full border rounded-md px-3 py-2"
                  placeholder="Leave empty for auto-generated"
                  disabled={newEmployeeModal.loading}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setNewEmployeeModal({
                  open: false, 
                  loading: false, 
                  username: '', 
                  email: '', 
                  first_name: '', 
                  last_name: '', 
                  employee_id: '', 
                  role: 'junior_staff',
                  affiliate_id: '', 
                  department_id: '', 
                  password: '',
                  hire_date: ''
                })}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                disabled={newEmployeeModal.loading}
              >
                Cancel
              </button>
              <button
                onClick={createEmployee}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-blue-600 text-white bg-blue-600 hover:bg-blue-700"
                disabled={newEmployeeModal.loading}
              >
                {newEmployeeModal.loading ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Affiliate Modal */}
      {newAffiliateModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
          <div className="bg-white rounded-md shadow p-6 w-full max-w-sm">
            <h3 className="text-lg font-semibold mb-4">Create New Affiliate</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Affiliate Name *</label>
                <input
                  type="text"
                  value={newAffiliateModal.name}
                  onChange={(e) => setNewAffiliateModal((prev) => ({ ...prev, name: e.target.value }))}
                  className="w-full border rounded-md px-3 py-2"
                  placeholder="e.g. MERBAN CAPITAL"
                  disabled={newAffiliateModal.loading}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={newAffiliateModal.description}
                  onChange={(e) => setNewAffiliateModal((prev) => ({ ...prev, description: e.target.value }))}
                  className="w-full border rounded-md px-3 py-2"
                  rows="3"
                  placeholder="Optional description"
                  disabled={newAffiliateModal.loading}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setNewAffiliateModal({ open: false, loading: false, name: '', description: '' })}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                disabled={newAffiliateModal.loading}
              >
                Cancel
              </button>
              <button
                onClick={createAffiliate}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-blue-600 text-white bg-blue-600 hover:bg-blue-700"
                disabled={newAffiliateModal.loading}
              >
                {newAffiliateModal.loading ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Employees Modal */}
      {deleteEmployeeModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
          <div className="bg-white rounded-md shadow p-6 w-full max-w-lg">
            <h3 className="text-lg font-semibold mb-4">Delete Employees</h3>
            {employees.length === 0 ? (
              <div className="text-sm text-gray-500">There are no employees to delete.</div>
            ) : (
              <>
                <div className="flex items-center justify-between mb-3">
                  <button
                    className="text-sm text-sky-600 hover:underline"
                    onClick={() => {
                      const all = {};
                      employees.forEach(e => { all[e.id] = true; });
                      setDeleteEmployeeModal(prev => ({ ...prev, selected: all }));
                    }}
                  >
                    Select all
                  </button>
                  <div className="text-sm text-gray-600">
                    Selected: {Object.values(deleteEmployeeModal.selected).filter(Boolean).length}
                  </div>
                </div>
                <div className="max-h-64 overflow-y-auto border rounded">
                  {employees.map((emp) => (
                    <label key={emp.id} className="flex items-start gap-3 p-3 border-b last:border-b-0">
                      <input
                        type="checkbox"
                        className="mt-1"
                        checked={!!deleteEmployeeModal.selected[emp.id]}
                        onChange={(e) => {
                          const checked = e.target.checked;
                          setDeleteEmployeeModal(prev => ({
                            ...prev,
                            selected: { ...prev.selected, [emp.id]: checked },
                          }));
                        }}
                      />
                      <div>
                        <div className="font-medium text-gray-900">{emp.name} <span className="text-gray-500">({emp.employee_id})</span></div>
                        <div className="text-sm text-gray-600">{emp.email} · {emp.role === 'ceo' ? '—' : (emp.department || '—')}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </>
            )}
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setDeleteEmployeeModal({ open: false, selected: {}, processing: false })}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                disabled={deleteEmployeeModal.processing}
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  const ids = Object.keys(deleteEmployeeModal.selected).filter((k) => deleteEmployeeModal.selected[k]).map(Number);
                  if (ids.length === 0) {
                    showToast({ type: 'warning', message: 'Select at least one employee to delete' });
                    return;
                  }
                  try {
                    setDeleteEmployeeModal(prev => ({ ...prev, processing: true }));
                    const results = await Promise.allSettled(ids.map((empId) => api.delete(`/users/${empId}/`)));
                    const failed = results.filter(r => r.status === 'rejected');
                    if (failed.length > 0) {
                      showToast({ type: 'warning', message: `Deleted ${ids.length - failed.length} of ${ids.length} employees (some failed)` });
                    } else {
                      showToast({ type: 'success', message: `Deleted ${ids.length} employee${ids.length === 1 ? '' : 's'}` });
                    }
                    await fetchStaffData();
                    setDeleteEmployeeModal({ open: false, selected: {}, processing: false });
                  } catch (e) {
                    const msg = e.response?.data?.detail || 'Failed to delete employees';
                    showToast({ type: 'error', message: msg });
                    setDeleteEmployeeModal(prev => ({ ...prev, processing: false }));
                  }
                }}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-red-600 text-white bg-red-600 hover:bg-red-700"
                disabled={deleteEmployeeModal.processing || Object.values(deleteEmployeeModal.selected).every(v => !v)}
              >
                {deleteEmployeeModal.processing ? 'Deleting...' : 'Delete selected'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Affiliates Modal */}
      {deleteAffiliateModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
          <div className="bg-white rounded-md shadow p-6 w-full max-w-lg">
            <h3 className="text-lg font-semibold mb-4">Delete Affiliates</h3>
            {affiliates.length === 0 ? (
              <div className="text-sm text-gray-500">There are no affiliates to delete.</div>
            ) : (
              <>
                <div className="flex items-center justify-between mb-3">
                  <button
                    className="text-sm text-sky-600 hover:underline"
                    onClick={() => {
                      const all = {};
                      affiliates.forEach(a => { all[a.id] = true; });
                      setDeleteAffiliateModal(prev => ({ ...prev, selected: all }));
                    }}
                  >
                    Select all
                  </button>
                  <div className="text-sm text-gray-600">
                    Selected: {Object.values(deleteAffiliateModal.selected).filter(Boolean).length}
                  </div>
                </div>
                <div className="max-h-64 overflow-y-auto border rounded">
                  {affiliates.map((a) => (
                    <label key={a.id} className="flex items-start gap-3 p-3 border-b last:border-b-0">
                      <input
                        type="checkbox"
                        className="mt-1"
                        checked={!!deleteAffiliateModal.selected[a.id]}
                        onChange={(e) => {
                          const checked = e.target.checked;
                          setDeleteAffiliateModal(prev => ({
                            ...prev,
                            selected: { ...prev.selected, [a.id]: checked },
                          }));
                        }}
                      />
                      <div>
                        <div className="font-medium text-gray-900">{a.name}</div>
                        {a.description && <div className="text-sm text-gray-600">{a.description}</div>}
                      </div>
                    </label>
                  ))}
                </div>
              </>
            )}
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setDeleteAffiliateModal({ open: false, selected: {}, processing: false })}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                disabled={deleteAffiliateModal.processing}
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  const ids = Object.keys(deleteAffiliateModal.selected).filter((k) => deleteAffiliateModal.selected[k]).map(Number);
                  if (ids.length === 0) {
                    showToast({ type: 'warning', message: 'Select at least one affiliate to delete' });
                    return;
                  }
                  try {
                    setDeleteAffiliateModal(prev => ({ ...prev, processing: true }));
                    const results = await Promise.allSettled(ids.map((affId) => api.delete(`/users/affiliates/${affId}/`)));
                    const failed = results.filter(r => r.status === 'rejected');
                    if (failed.length > 0) {
                      showToast({ type: 'warning', message: `Deleted ${ids.length - failed.length} of ${ids.length} affiliates (some failed)` });
                    } else {
                      showToast({ type: 'success', message: `Deleted ${ids.length} affiliate${ids.length === 1 ? '' : 's'}` });
                    }
                    await fetchAffiliates();
                    // Departments may have been cascaded; refresh staff data too
                    await fetchStaffData();
                    setDeleteAffiliateModal({ open: false, selected: {}, processing: false });
                  } catch (e) {
                    const msg = e.response?.data?.detail || 'Failed to delete affiliates';
                    showToast({ type: 'error', message: msg });
                    setDeleteAffiliateModal(prev => ({ ...prev, processing: false }));
                  }
                }}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-red-600 text-white bg-red-600 hover:bg-red-700"
                disabled={deleteAffiliateModal.processing || Object.values(deleteAffiliateModal.selected).every(v => !v)}
              >
                {deleteAffiliateModal.processing ? 'Deleting...' : 'Delete selected'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Leave History Modal */}
      {leaveHistoryModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
          <div className="bg-white rounded-md shadow p-6 w-full max-w-4xl max-h-[80vh]">
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
              <div className="overflow-y-auto max-h-[60vh]">
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
            
            <div className="flex justify-end mt-6">
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

      {/* HOD Management Modal */}
      {hodModal.open && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">
                Set HOD for {hodModal.department?.name}
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                Select a manager to serve as Head of Department (HOD) for approval of leave requests.
              </p>
            </div>
            
            <div className="px-6 py-4">
              {hodModal.loading ? (
                <div className="flex justify-center py-4">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Select Manager/HOD
                  </label>
                  <select
                    value={hodModal.selectedManagerId}
                    onChange={(e) => setHodModal(prev => ({ ...prev, selectedManagerId: e.target.value }))}
                    className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                  >
                    <option value="">-- No HOD (Remove current) --</option>
                    {employees
                      .filter(emp => emp.department === hodModal.department?.name)
                      .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
                      .map(emp => (
                        <option key={emp.id} value={emp.id}>
                          {emp.name} ({emp.employee_id})
                        </option>
                      ))}
                  </select>
                  
                  {hodModal.department?.manager && (
                    <div className="mt-3 p-3 bg-blue-50 rounded border border-blue-200">
                      <p className="text-sm text-blue-800">
                        <span className="font-medium">Current HOD:</span> {hodModal.department.manager.name} ({hodModal.department.manager.employee_id})
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
            
            <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={() => setHodModal({ open: false, loading: false, department: null, selectedManagerId: '' })}
                disabled={hodModal.loading}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={updateDepartmentHod}
                disabled={hodModal.loading}
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 disabled:opacity-50"
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

export default StaffManagement;

function LeaveTypesList({ onConfigure }) {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [types, setTypes] = useState([]);

  const load = useCallback(async () => {
    try {
      const res = await api.get('/leaves/types/');
      setTypes(res.data.results || res.data || []);
    } catch (e) {
      showToast({ type: 'error', message: 'Failed to load leave types' });
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <div className="text-sm text-gray-500">Loading leave types...</div>;

  if (!types.length) return <div className="text-sm text-gray-500">No leave types found.</div>;

  return (
    <ul className="space-y-2">
      {types.map((t) => (
        <li key={t.id} className="px-3 py-2 bg-gray-50 rounded-md flex justify-between items-center">
          <div>
            <div className="font-medium">{t.name}</div>
            {t.description && <div className="text-xs text-gray-500">{t.description}</div>}
          </div>
          <button
            onClick={() => onConfigure(t)}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
          >
            Configure
          </button>
        </li>
      ))}
    </ul>
  );
}

