import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';

function RoleManagement() {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [roles, setRoles] = useState([]);
  const [leaveTypes, setLeaveTypes] = useState([]);
  const [selectedRole, setSelectedRole] = useState(null);
  const [configuring, setConfiguring] = useState(false);
  const [entitlements, setEntitlements] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchRoleData();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchRoleData = async () => {
    try {
      setLoading(true);
      const response = await api.get('/leaves/role-entitlements/');
      setRoles(response.data.roles || []);
      setLeaveTypes(response.data.leave_types || []);
    } catch (error) {
      console.error('Failed to fetch role data:', error);
      showToast({ type: 'error', message: 'Failed to load role data' });
    } finally {
      setLoading(false);
    }
  };

  const selectRole = async (roleCode) => {
    try {
      setConfiguring(true);
      const response = await api.get(`/leaves/role-entitlements/${roleCode}/summary/`);
      setSelectedRole(response.data);
      
      // Convert entitlements array to object for easier editing
      const entitlementsObj = {};
      response.data.entitlements.forEach(ent => {
        entitlementsObj[ent.leave_type_id] = ent.entitled_days;
      });
      setEntitlements(entitlementsObj);
    } catch (error) {
      console.error('Failed to fetch role summary:', error);
      showToast({ type: 'error', message: 'Failed to load role details' });
    } finally {
      setConfiguring(false);
    }
  };

  const updateEntitlement = (leaveTypeId, days) => {
    setEntitlements(prev => ({
      ...prev,
      [leaveTypeId]: Math.max(0, parseInt(days) || 0)
    }));
  };

  const saveEntitlements = async () => {
    if (!selectedRole) return;

    try {
      setSaving(true);
      
      // Convert entitlements object back to array format
      const entitlementsArray = Object.entries(entitlements).map(([leaveTypeId, days]) => ({
        leave_type_id: parseInt(leaveTypeId),
        entitled_days: parseInt(days)
      }));

      const response = await api.post(
        `/leaves/role-entitlements/${selectedRole.role_code}/set_entitlements/`,
        { entitlements: entitlementsArray }
      );

      showToast({ 
        type: 'success', 
        message: `Entitlements updated for ${selectedRole.role_display}. ${response.data.users_affected} users affected.`
      });

      // Refresh the role data
      await fetchRoleData();
      
      // Update selected role data
      await selectRole(selectedRole.role_code);
      
    } catch (error) {
      console.error('Failed to save entitlements:', error);
      const errorMessage = error.response?.data?.error || 'Failed to save entitlements';
      showToast({ type: 'error', message: errorMessage });
    } finally {
      setSaving(false);
    }
  };

  const getRoleIcon = (roleCode) => {
    const icons = {
      junior_staff: '👤',
      senior_staff: '👨‍💼',
      manager: '👔',
      hr: '👩‍💼',
      admin: '👑'
    };
    return icons[roleCode] || '👤';
  };

  const getRoleColor = (roleCode) => {
    const colors = {
      junior_staff: 'bg-blue-100 text-blue-800 border-blue-200',
      senior_staff: 'bg-green-100 text-green-800 border-green-200',
      manager: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      hr: 'bg-purple-100 text-purple-800 border-purple-200',
      admin: 'bg-red-100 text-red-800 border-red-200'
    };
    return colors[roleCode] || 'bg-gray-100 text-gray-800 border-gray-200';
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-sky-500 border-t-transparent"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-medium mb-2">Role Management</h2>
        <p className="text-sm text-gray-600 mb-6">
          Configure leave entitlements by employee role. Changes will apply to all users with the selected role.
        </p>
      </div>

      {!selectedRole ? (
        /* Role Selection View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {roles.map((role) => (
            <div
              key={role.role_code}
              className={`p-6 border-2 rounded-lg cursor-pointer hover:shadow-md transition-all ${getRoleColor(role.role_code)}`}
              onClick={() => selectRole(role.role_code)}
            >
              <div className="flex items-center gap-3 mb-3">
                <span className="text-2xl">{getRoleIcon(role.role_code)}</span>
                <div>
                  <h3 className="font-semibold text-lg">{role.role_display}</h3>
                  <p className="text-sm opacity-75">{role.user_count} user{role.user_count !== 1 ? 's' : ''}</p>
                </div>
              </div>
              
              <div className="space-y-2">
                <div className="text-xs font-medium opacity-75">Current Entitlements:</div>
                {role.entitlements.slice(0, 3).map((ent) => (
                  <div key={ent.leave_type_id} className="flex justify-between text-xs">
                    <span>{ent.leave_type_name}:</span>
                    <span className="font-medium">{ent.entitled_days} days</span>
                  </div>
                ))}
                {role.entitlements.length > 3 && (
                  <div className="text-xs opacity-75">+{role.entitlements.length - 3} more...</div>
                )}
              </div>
              
              <div className="mt-4 text-xs font-medium opacity-75">
                Click to configure →
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Role Configuration View */
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{getRoleIcon(selectedRole.role_code)}</span>
              <div>
                <h3 className="text-xl font-semibold">{selectedRole.role_display}</h3>
                <p className="text-sm text-gray-600">
                  {selectedRole.user_count} user{selectedRole.user_count !== 1 ? 's' : ''} • {selectedRole.year}
                </p>
              </div>
            </div>
            <button
              onClick={() => setSelectedRole(null)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
            >
              ← Back to Roles
            </button>
          </div>

          {configuring ? (
            <div className="flex justify-center items-center h-32">
              <div className="animate-spin rounded-full h-6 w-6 border-2 border-sky-500 border-t-transparent"></div>
            </div>
          ) : (
            <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                <h4 className="text-sm font-medium text-gray-900">Leave Entitlements</h4>
                <p className="text-xs text-gray-600">Set the number of days for each leave type</p>
              </div>
              
              <div className="divide-y divide-gray-200">
                {leaveTypes.map((leaveType) => (
                  <div key={leaveType.id} className="px-4 py-4 flex items-center justify-between">
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">{leaveType.name}</div>
                      {leaveType.description && (
                        <div className="text-sm text-gray-600">{leaveType.description}</div>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        min="0"
                        max="365"
                        value={entitlements[leaveType.id] || 0}
                        onChange={(e) => updateEntitlement(leaveType.id, e.target.value)}
                        className="w-20 px-2 py-1 border border-gray-300 rounded text-center"
                        disabled={saving}
                      />
                      <span className="text-sm text-gray-600">days</span>
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex justify-end gap-2">
                <button
                  onClick={() => setSelectedRole(null)}
                  className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  onClick={saveEntitlements}
                  className="px-4 py-2 text-sm bg-sky-600 text-white rounded-md hover:bg-sky-700 disabled:opacity-50"
                  disabled={saving}
                >
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default RoleManagement;