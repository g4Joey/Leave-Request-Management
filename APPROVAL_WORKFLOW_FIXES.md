# Approval Workflow Fixes - Production Issues Resolved

## Issues Addressed

### 1. HR User's Own Leave Request Shows Wrong Status
**Problem**: HR user requests leave, status shows "Pending Manager Approval" but should show "Pending CEO Approval" since HR requests skip both manager and HR approval stages.

**Solution**: 
- Added `get_dynamic_status_display()` method to LeaveRequest model that determines the correct status label based on the employee's role and approval workflow
- Updated LeaveRequestSerializer to use `get_dynamic_status_display()` instead of `get_status_display()`
- HR requests now correctly show "Pending CEO Approval"

### 2. Manager/HOD Requests Not Showing in HR Approval Queue
**Problem**: Manager/HOD requests were not appearing in HR approval queue because the queue only looked for `manager_approved` status, but manager/HOD requests have status=`pending` and skip the manager approval stage.

**Solution**:
- Updated HR approval queue filter in `pending_approvals()` to include:
  - Merban staff requests with status=`manager_approved`
  - Merban manager/HOD/HR requests with status=`pending` (skip-manager flow)
  - All ceo_approved requests (SDSL/SBL final HR approval)
- Updated HR approval counts in `approval_counts()` to match the queue logic
- Manager/HOD requests now correctly appear in HR approval queue

### 3. Admin Approval Counts Not Matching Actual Queue Items
**Problem**: Admin manager approval count was including manager/CEO/HR role requests when it should only show staff requests.

**Solution**:
- Updated admin manager queue filter to exclude `['manager', 'hr', 'ceo', 'admin']` roles (staff-only)
- Updated admin HR queue count to include:
  - Merban staff manager_approved
  - Merban manager/HOD/HR pending (skip-manager flow)
  - All CEO-approved requests
- Admin counts now accurately reflect the actual queue contents

### 4. Admin Can Approve at Wrong Workflow Stages
**Problem**: Admin users could approve requests at any stage, even when the workflow hadn't reached that stage yet (e.g., approving at CEO stage when request should be at HR stage).

**Solution**:
- Updated `can_approve()` method in ApprovalHandler to ensure admin respects workflow stages
- Admin can only approve at stages that exist in the current workflow
- Admin cannot act as CEO (removed blanket CEO approval permission for non-superuser admins)
- Admin workflow permissions now follow proper approval stage progression

## Technical Changes

### Files Modified:

1. **leaves/models.py**
   - Added `get_dynamic_status_display()` method to LeaveRequest model
   - Returns contextually appropriate status labels based on employee role and workflow

2. **leaves/serializers.py**
   - Updated LeaveRequestSerializer to use `get_dynamic_status_display()`
   - Status labels now reflect actual approval workflow

3. **leaves/views.py**
   - Updated HR pending_approvals queue filter to include manager/HOD/HR pending requests
   - Updated HR approval_counts logic to match queue filtering
   - Updated admin manager queue to exclude all non-staff roles
   - Updated admin HR queue counts to include manager/HOD/HR pending requests

4. **leaves/services.py**
   - Updated `can_approve()` method to enforce workflow stage progression for admin
   - Admin can no longer approve at arbitrary stages
   - Regular admin cannot act as CEO (only superuser can)

## Workflow Summary

### Merban Capital Approval Flows:

**Staff**: Manager → HR → CEO
**Manager/HOD**: HR → CEO (skip manager stage)
**HR**: CEO only (skip manager and HR stages)

### SDSL/SBL Approval Flows:

**All employees**: CEO → HR (CEO first, HR final)

## Testing

All fixes verified with diagnostic script showing:
- ✅ HR requests show "Pending CEO Approval"
- ✅ Manager requests show "Pending HR Approval"  
- ✅ Manager/HOD/HR requests appear in HR approval queue
- ✅ Admin approval counts match actual queue contents
- ✅ Admin respects workflow stage progression
- ✅ Approval routing follows correct affiliate-based CEO assignment

## Production Deployment Notes

These changes fix critical approval workflow issues and should be deployed to production immediately. All changes are backward-compatible and do not require database migrations.

**Important**: The dynamic status display will only affect new API responses. Frontend may need to refresh to see updated status labels.
