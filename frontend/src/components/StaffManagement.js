import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';

const SIDEBAR_ITEMS = [
  { id: 'departments', label: 'Departments' },
  { id: 'employees', label: 'Employees' },
  { id: 'leave-types', label: 'Leave Types' },
  { id: 'leave-policies', label: 'Leave Policies' },
  { id: 'import', label: 'Import' },
  { id: 'export', label: 'Export' },
];

function StaffManagement() {
  const { showToast } = useToast();
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedDepts, setExpandedDepts] = useState({});
  const [active, setActive] = useState(SIDEBAR_ITEMS[0].id);
  const [employees, setEmployees] = useState([]);
  const [employeeQuery, setEmployeeQuery] = useState('');
  const fileInputRef = useRef(null);

  // Remove trailing role words accidentally saved in last names (e.g., "Ato Manager")
  const cleanName = (name) => {
    if (!name || typeof name !== 'string') return name;
    return name.replace(/\s+(Manager|Staff|HR|Admin)$/i, '').trim();
  };

  const fetchStaffData = useCallback(async () => {
    try {
      const response = await api.get('/users/staff/');
      const depts = response.data || [];
      setDepartments(depts);
      // Flatten employees for the Employees tab
      const flattened = depts.flatMap((d) =>
        (d.staff || []).map((s) => ({
          id: s.id,
          name: cleanName(s.name),
          email: s.email,
          department: d.name,
          employee_id: s.employee_id,
          role: s.role,
          manager: s.manager,
          hire_date: s.hire_date,
        }))
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

  const toggleDepartment = (deptId) => {
    setExpandedDepts((prev) => ({
      ...prev,
      [deptId]: !prev[deptId],
    }));
  };

  const getRoleBadge = (role) => {
    const roleColors = {
      staff: 'bg-gray-100 text-gray-800',
      manager: 'bg-blue-100 text-blue-800',
      hr: 'bg-green-100 text-green-800',
      admin: 'bg-purple-100 text-purple-800',
    };

    return (
      <span
        className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
          roleColors[role] || roleColors.staff
        }`}
      >
        {role?.charAt(0).toUpperCase() + role?.slice(1)}
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
                onClick={() => setActive('departments')}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
              >
                New department
              </button>
              <button
                onClick={() => setActive('employees')}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
              >
                New employee
              </button>
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
                            <div className="flex flex-wrap gap-2">
                              <button
                                onClick={() => showToast({ type: 'info', message: `Open profile for ${emp.name}` })}
                                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-gray-200"
                              >
                                Profile
                              </button>
                              <button
                                onClick={() => showToast({ type: 'info', message: `Set leave benefits for ${emp.name}` })}
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
                <ul className="space-y-2">
                  {['Annual', 'Sick', 'Maternity', 'Paternity', 'Compassionate', 'Casual'].map((t) => (
                    <li key={t} className="px-3 py-2 bg-gray-50 rounded-md flex justify-between items-center">
                      <span>{t}</span>
                      <div className="text-sm text-gray-500">configure</div>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {active === 'leave-policies' && (
              <section>
                <h2 className="text-lg font-medium mb-4">Leave Policies</h2>
                <p className="text-sm text-gray-600 mb-4">Create rules and entitlements (carryover, blackout dates, max continuous days)</p>
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
    </div>
  );
}

export default StaffManagement;