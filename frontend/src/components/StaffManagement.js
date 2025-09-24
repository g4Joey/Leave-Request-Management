import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';

function StaffManagement() {
  const { showToast } = useToast();
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedDepts, setExpandedDepts] = useState({});

  // Remove trailing role words accidentally saved in last names (e.g., "Ato Manager")
  const cleanName = (name) => {
    if (!name || typeof name !== 'string') return name;
    return name.replace(/\s+(Manager|Staff|HR|Admin)$/i, '').trim();
  };

  const fetchStaffData = useCallback(async () => {
    try {
      const response = await api.get('/users/staff/');
      setDepartments(response.data);
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
    setExpandedDepts(prev => ({
      ...prev,
      [deptId]: !prev[deptId]
    }));
  };

  const getRoleBadge = (role) => {
    const roleColors = {
      'staff': 'bg-gray-100 text-gray-800',
      'manager': 'bg-blue-100 text-blue-800',
      'hr': 'bg-green-100 text-green-800',
      'admin': 'bg-purple-100 text-purple-800'
    };
    
    return (
      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${roleColors[role] || roleColors.staff}`}>
        {role.charAt(0).toUpperCase() + role.slice(1)}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="bg-white shadow overflow-hidden sm:rounded-md">
      <div className="px-4 py-5 sm:px-6">
        <h3 className="text-lg leading-6 font-medium text-gray-900">
          Staff Management
        </h3>
        <p className="mt-1 max-w-2xl text-sm text-gray-500">
          View and manage staff by department.
        </p>
      </div>

      <div className="border-t border-gray-200">
        {departments.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 px-4 pb-6">
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
                        <div
                          key={staff.id}
                          className="bg-gray-50 rounded-lg p-4 border border-gray-200"
                        >
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
                    <div className="text-sm text-gray-500 italic">
                      No staff members in this department.
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
          </div>
        ) : (
          <div className="px-4 py-8 text-center text-gray-500">
            No departments found.
          </div>
        )}
      </div>
    </div>
  );
}

export default StaffManagement;