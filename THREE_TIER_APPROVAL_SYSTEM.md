# Three-Tier Leave Approval System

## Overview
This system implements a three-tier approval workflow for leave requests:
**Staff → Manager → HR → CEO**

## Approval Workflow

### 1. Staff Submits Leave Request
- Employee creates leave request via API or frontend
- Status: `pending`
- Notification sent to their manager
- If no manager assigned, notification goes to HR

### 2. Manager Approval (Stage 1)
- Manager reviews and approves/rejects the request
- **If Approved**: Status changes to `manager_approved`, forwarded to HR
- **If Rejected**: Status changes to `rejected`, notifications sent to employee
- Notifications sent to employee and HR team

### 3. HR Approval (Stage 2)
- HR reviews manager-approved requests
- **If Approved**: Status changes to `hr_approved`, forwarded to CEO
- **If Rejected**: Status changes to `rejected`, notifications sent to employee and manager
- Notifications sent to employee, manager, and CEO

### 4. CEO Final Approval (Stage 3)
- CEO reviews HR-approved requests
- **If Approved**: Status changes to `approved` (final), leave balance updated
- **If Rejected**: Status changes to `rejected`, notifications sent to all parties
- Notifications sent to employee, manager, and HR

## User Roles

### CEO Role
- Username: `ceo`
- Role: `ceo`
- Can approve requests at stage 3 (final approval)
- Can see pending requests that have passed HR approval

### Existing Roles Extended
- **Manager**: Stage 1 approval
- **HR**: Stage 2 approval  
- **Admin**: Can approve at any stage (override capability)
- **Staff**: Can only submit requests

## API Endpoints

### Approval Dashboard
```
GET /api/leaves/approval-dashboard/
```
Returns approval statistics and pending requests for current user's role.

### Pending Approvals (Role-Filtered)
```
GET /api/leaves/manager/pending_approvals/
```
Returns requests pending approval based on user's role:
- **Manager**: Requests with status `pending`
- **HR**: Requests with status `manager_approved`
- **CEO**: Requests with status `hr_approved`
- **Admin**: All pending requests

### Approve Request
```
PUT /api/leaves/manager/{id}/approve/
Body: {"approval_comments": "Approved - good reason"}
```

### Reject Request
```
PUT /api/leaves/manager/{id}/reject/
Body: {"approval_comments": "Rejected - conflicts with busy period"}
```

## Database Changes

### New LeaveRequest Fields
- `manager_approved_by`, `manager_approval_date`, `manager_approval_comments`
- `hr_approved_by`, `hr_approval_date`, `hr_approval_comments`
- `ceo_approved_by`, `ceo_approval_date`, `ceo_approval_comments`

### Updated Status Choices
- `pending`: Pending Manager Approval
- `manager_approved`: Manager Approved - Pending HR
- `hr_approved`: HR Approved - Pending CEO
- `approved`: Fully Approved
- `rejected`: Rejected
- `cancelled`: Cancelled

### New Notification Types
- `leave_manager_approved`: Leave Request Approved by Manager
- `leave_hr_approved`: Leave Request Approved by HR
- `leave_approved`: Leave Request Fully Approved

## Setup Instructions

### 1. Apply Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Create CEO User
```bash
python manage.py create_ceo
# Creates CEO with username 'ceo' and default password 'ChangeMe123!'
```

### 3. Test the System
```bash
# Test the workflow programmatically
python test_approval_workflow.py

# Test via API calls
python test_api_approval_workflow.py
```

## Notification Flow

### When Leave is Submitted
- **Sent to**: Employee's manager (or HR if no manager)

### When Manager Approves
- **Sent to**: Employee (status update), All HR users (new request)

### When HR Approves  
- **Sent to**: Employee (status update), Manager (status update), All CEOs (new request)

### When CEO Approves (Final)
- **Sent to**: Employee (congratulations), Manager (status update), All HR users (status update)

### When Anyone Rejects
- **Sent to**: Employee (always), Previous approvers based on stage
- **Manager rejection**: Only employee notified
- **HR rejection**: Employee and manager notified
- **CEO rejection**: Employee, manager, and HR notified

## Business Rules

1. **Sequential Approval**: Must follow Manager → HR → CEO order
2. **Role-Based Access**: Users can only approve at their designated stage
3. **Balance Updates**: Leave balance only updated on final CEO approval
4. **Admin Override**: Admin users can approve at any stage
5. **Rejection Stops Process**: Any rejection ends the workflow
6. **Notification Chain**: All stakeholders kept informed at each stage

## Frontend Integration Notes

The frontend should:
1. Show different pending queues based on user role
2. Display approval history with all three stages
3. Show current approval stage clearly
4. Provide role-appropriate action buttons
5. Display notification count by approval stage

## Testing

### Test Users Created
- **CEO**: `ceo` / `ChangeMe123!`
- **Existing HR**: Use existing HR users
- **Existing Managers**: Use existing manager users  
- **Staff**: Use existing staff users

### Test Scenarios
1. ✅ Complete approval workflow (Manager → HR → CEO)
2. ✅ Manager rejection
3. ✅ HR rejection  
4. ✅ CEO rejection
5. ✅ Admin override approval
6. ✅ Notification delivery
7. ✅ Leave balance updates

## Security Considerations

1. **Role Verification**: Users cannot approve beyond their authority level
2. **Request Ownership**: Only assigned approvers can act on requests
3. **Audit Trail**: All approval actions logged with timestamps and comments
4. **Token Authentication**: All API endpoints require authentication
5. **Permission Checks**: Role-based permission validation at each stage