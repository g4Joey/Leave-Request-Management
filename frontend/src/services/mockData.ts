export const MOCK_USER = {
  id: 1,
  email: 'demo@leavemates.com',
  first_name: 'Demo',
  last_name: 'User',
  role: 'employee', // Change this to 'manager', 'hr', 'consultant' to test different views
  role_display: 'Employee',
  is_superuser: false,
  department: { id: 1, name: 'Engineering' },
  affiliate: null,
  annual_leave_entitlement: 20,
  phone: '123-456-7890',
  profile_image: null,
  grade: { id: 1, name: 'Grade A', slug: 'grade-a' }
};

export const MOCK_LEAVE_TYPES = [
  { id: 1, name: 'Annual Leave', days_allowed: 20 },
  { id: 2, name: 'Sick Leave', days_allowed: 10 },
  { id: 3, name: 'Remote Work', days_allowed: 50 },
  { id: 4, name: 'Unpaid Leave', days_allowed: 0 }
];

export const MOCK_LEAVE_REQUESTS = [
  {
    id: 101,
    leave_type: 'Annual Leave',
    start_date: '2025-01-10',
    end_date: '2025-01-15',
    days_requested: 5,
    status: 'approved',
    reason: 'Family vacation',
    created_at: '2025-01-01'
  },
  {
    id: 102,
    leave_type: 'Sick Leave',
    start_date: '2025-02-05',
    end_date: '2025-02-06',
    days_requested: 2,
    status: 'pending',
    reason: 'Flu',
    created_at: '2025-02-04'
  }
];

export const MOCK_STATS = {
  total_leaves: 15,
  approved: 10,
  pending: 2,
  rejected: 3,
  remaining_allowance: 12
};
