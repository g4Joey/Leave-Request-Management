/**
 * Utility functions for handling role display and mapping
 */

// Map database roles to user-friendly display names
export const getRoleDisplayName = (role) => {
  const roleDisplayMap = {
    junior_staff: 'Junior Staff',
    senior_staff: 'Senior Staff', 
    manager: 'HOD (Head of Department)',
    hr: 'HR',
    ceo: 'CEO',
    admin: 'Admin'
  };
  
  return roleDisplayMap[role] || role;
};

// Get short display name for badges and dropdowns
export const getRoleShortName = (role) => {
  const roleShortMap = {
    junior_staff: 'Junior Staff',
    senior_staff: 'Senior Staff', 
    manager: 'HOD',
    hr: 'HR',
    ceo: 'CEO', 
    admin: 'Admin'
  };
  
  return roleShortMap[role] || role;
};

// Get role colors for badges
export const getRoleColor = (role) => {
  const roleColors = {
    junior_staff: 'bg-gray-100 text-gray-800',
    senior_staff: 'bg-slate-100 text-slate-800',
    manager: 'bg-blue-100 text-blue-800',
    hr: 'bg-green-100 text-green-800',
    ceo: 'bg-indigo-100 text-indigo-800',
    admin: 'bg-purple-100 text-purple-800'
  };
  
  return roleColors[role] || roleColors.junior_staff;
};