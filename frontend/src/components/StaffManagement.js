import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { useAuth } from '../contexts/AuthContext';
import RoleManagement from './RoleManagement';

// Base sidebar items (grade-entitlements will be conditionally included for privileged roles)
const BASE_SIDEBAR_ITEMS = [
  { id: 'departments', label: 'Departments' },
  { id: 'employees', label: 'Employees' },
  { id: 'leave-types', label: 'Leave Types' },
  { id: 'leave-policies', label: 'Leave Policies' },
  { id: 'import', label: 'Import' },
  { id: 'export', label: 'Export' },
];

function StaffManagement() {
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
  const [loading, setLoading] = useState(true);
  const [expandedDepts, setExpandedDepts] = useState({});
  const [active, setActive] = useState('departments');
  const [employees, setEmployees] = useState([]);
  const [employeeQuery, setEmployeeQuery] = useState('');
  const fileInputRef = useRef(null);
  const [leaveTypeModal, setLeaveTypeModal] = useState({ open: false, name: '', id: null, value: '' , loading: false});
  const [profileModal, setProfileModal] = useState({ open: false, loading: false, employee: null, data: null, error: null });
  const [profileRoleSaving, setProfileRoleSaving] = useState(false);
  const [benefitsModal, setBenefitsModal] = useState({ open: false, loading: false, employee: null, rows: [] });
  const [newDepartmentModal, setNewDepartmentModal] = useState({ open: false, loading: false, name: '', description: '' });
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

  // Remove trailing role words accidentally saved in last names (e.g., "Ato Manager")
  const cleanName = (name) => {
    if (!name || typeof name !== 'string') return name;
    return name.replace(/\s+(Manager|Staff|HR|Admin)$/i, '').trim();
  };

  const fetchStaffData = useCallback(async () => {
    try {
      const response = await api.get('/users/staff/');
    const depts = response.data.results || response.data || [];
      setDepartments(depts);
      // Flatten employees for the Employees tab
      const flattened = depts.flatMap((d) =>
        (d.staff || []).map((s) => {

          return {
            id: s.id,
            name: cleanName(s.name),
            email: s.email,
            department: d.name,
            employee_id: s.employee_id,
            role: s.role,
            manager: s.manager,
            hire_date: s.hire_date,
          };
        })
      );
      setEmployees(flattened);
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
        role: raw.role,
        department_name: raw.department?.name || raw.department_name || (typeof raw.department === 'string' ? raw.department : undefined),
        hire_date: raw.hire_date,
        first_name: raw.first_name,
        last_name: raw.last_name,
        grade: raw.grade || null,
      };
      console.log('[StaffManagement] Normalized profile response:', normalized);
      setProfileModal({ open: true, loading: false, employee: emp, data: normalized, error: null });
      setSelectedRole(normalized.role || 'junior_staff');
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
    const roleColors = {
      junior_staff: 'bg-gray-100 text-gray-800',
      senior_staff: 'bg-slate-100 text-slate-800',
      manager: 'bg-blue-100 text-blue-800',
      hr: 'bg-green-100 text-green-800',
      admin: 'bg-purple-100 text-purple-800',
    };

    const displayName = role?.replace('_', ' ')?.replace(/\b\w/g, l => l.toUpperCase()) || 'Staff';
    
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
      department_id: '', 
      password: '',
      hire_date: ''
    });
  };

  const createEmployee = async () => {
    const { username, email, first_name, last_name, employee_id, role, department_id, password, hire_date } = newEmployeeModal;
    
    if (!username.trim() || !email.trim() || !first_name.trim() || !employee_id.trim() || !role) {
      showToast({ type: 'warning', message: 'Username, email, first name, employee ID, and role are required' });
      return;
    }
    
    try {
      setNewEmployeeModal((prev) => ({ ...prev, loading: true }));
      const data = {
        username: username.trim(),
        email: email.trim(),
        first_name: first_name.trim(),
        last_name: last_name.trim(),
        employee_id: employee_id.trim(),
        role,
        is_active_employee: true
      };
      
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
        role: 'staff', 
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

  const handleImportFile = (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
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
        const nameIdx = header.indexOf('name');
        const emailIdx = header.indexOf('email');
        const deptIdx = header.indexOf('department');
        const idStart = employees.length + 1;
        const parsed = rows.map((r, i) => {
          const cols = r.split(',').map((c) => c.trim());
          return {
            id: idStart + i,
            name: cols[nameIdx] || '',
            email: cols[emailIdx] || '',
            department: cols[deptIdx] || '',
            employee_id: '',
            role: 'staff',
          };
        });
        setEmployees((prev) => [...prev, ...parsed]);
        showToast({ type: 'success', message: `Imported ${parsed.length} employees` });
      } catch (err) {
        showToast({ type: 'error', message: 'Failed to import CSV' });
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
    const csv = 'name,email,department\n';
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'employees_template.csv';
    a.click();
    URL.revokeObjectURL(url);
    showToast({ type: 'info', message: 'Downloaded CSV template' });
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
              {active === 'employees' && (
                <button
                  onClick={openNewEmployeeModal}
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                >
                  New employee
                </button>
              )}
            </div>
          </div>

          <div className="bg-white shadow rounded-md p-4 sm:p-6">
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
                            </div>
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
                          <td className="px-3 py-2">{emp.department}</td>
                          <td className="px-3 py-2">{emp.employee_id}</td>
                          <td className="px-3 py-2">{getRoleBadge(emp.role)}</td>
                          <td className="px-3 py-2">
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                              {emp.grade || '—'}
                            </span>
                          </td>
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
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

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
                <p className="text-sm text-gray-600 mb-4">Use a CSV with columns: name,email,department.</p>
                <div className="flex flex-wrap items-center gap-3">
                  <button
                    onClick={downloadTemplateCSV}
                    className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200 text-sky-700"
                  >
                    Download template (CSV)
                  </button>
                  <input ref={fileInputRef} type="file" accept="text/csv" onChange={handleImportFile} />
                </div>
                <p className="text-xs text-gray-500 mt-2">Note: This demo import updates only the local view and does not persist to the server.</p>
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
              <div className="space-y-2 text-sm">
                {(() => { console.log('[StaffManagement] Rendering profile modal with data:', profileModal.data); return null; })()}
                <div><span className="font-medium">Employee ID:</span> {profileModal.data.employee_id || '—'}</div>
                <div><span className="font-medium">Email:</span> {profileModal.data.email || '—'}</div>
                <div><span className="font-medium">Role:</span> {profileModal.data.role || '—'}</div>
                <div><span className="font-medium">Department:</span> {profileModal.data.department_name || '—'}</div>
                {profileModal.data.hire_date ? (
                  <div><span className="font-medium">Hire Date:</span> {new Date(profileModal.data.hire_date).toLocaleDateString()}</div>
                ) : (
                  <div><span className="font-medium">Hire Date:</span> —</div>
                )}
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
                      <option value="manager">Manager</option>
                      <option value="hr">HR</option>
                      <option value="admin">Admin</option>
                    </select>
                    <button
                      onClick={saveProfileRole}
                      disabled={profileRoleSaving || (profileModal.data.role || 'junior_staff') === selectedRole}
                      className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border border-sky-600 text-white bg-sky-600 disabled:opacity-50"
                    >
                      {profileRoleSaving ? 'Saving...' : 'Save'}
                    </button>
                  </div>
                </div>
              </div>
            )}
            {!profileModal.loading && !profileModal.error && !profileModal.data && (
              <div className="text-sm text-gray-500 italic">No profile data available.</div>
            )}
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setProfileModal({ open: false, loading: false, employee: null, data: null })} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200">Close</button>
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
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Username *</label>
                  <input
                    type="text"
                    value={newEmployeeModal.username}
                    onChange={(e) => setNewEmployeeModal((prev) => ({ ...prev, username: e.target.value }))}
                    className="w-full border rounded-md px-3 py-2"
                    placeholder="john.doe"
                    disabled={newEmployeeModal.loading}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Employee ID *</label>
                  <input
                    type="text"
                    value={newEmployeeModal.employee_id}
                    onChange={(e) => setNewEmployeeModal((prev) => ({ ...prev, employee_id: e.target.value }))}
                    className="w-full border rounded-md px-3 py-2"
                    placeholder="EMP001"
                    disabled={newEmployeeModal.loading}
                  />
                </div>
              </div>
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
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
                    <option value="manager">Manager</option>
                    <option value="hr">HR</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Department</label>
                  <select
                    value={newEmployeeModal.department_id}
                    onChange={(e) => setNewEmployeeModal((prev) => ({ ...prev, department_id: e.target.value }))}
                    className="w-full border rounded-md px-3 py-2"
                    disabled={newEmployeeModal.loading}
                  >
                    <option value="">Select Department</option>
                    {departments.map((dept) => (
                      <option key={dept.id} value={dept.id}>{dept.name}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
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
                  role: 'staff', 
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

