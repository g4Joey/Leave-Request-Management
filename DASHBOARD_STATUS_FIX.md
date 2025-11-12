# Dashboard Status Display Fix - November 12, 2025

## Issues Fixed

### 1. ✅ Departments Synced to Production
**Task:** Update local departments to match production canonical list

**Canonical Departments (Merban Capital):**
1. Finance & Accounts
2. Government Securities
3. Pensions & Provident Fund
4. Private Wealth & Mutual Fund
5. HR & Admin
6. Client Service/Marketing
7. Corporate Finance
8. IT
9. Compliance
10. Audit

**Result:**
- All 10 canonical departments exist
- Removed "Executive" department (0 users, non-canonical)

### 2. ✅ Deleted Eric Nartey
**Task:** Remove Eric Nartey from local database

**Result:**
- User: Eric Nartey (staff@sbl.com)
- Role: senior_staff (SBL)
- Successfully deleted from database

### 3. ✅ Fixed Dashboard Status Display
**Problem:** 
- Manager/HR requests showed "Pending Manager Approval" in "Recent Leave Requests"
- Should show "Pending HR Approval" for managers/HR

**Root Cause:**
- `LeaveRequestListSerializer` used `get_status_display()` (Django default) instead of `get_dynamic_status_display()`
- Dashboard view was overriding `status_display` with `stage_label` which had hardcoded logic

**Solution:**
1. Updated `LeaveRequestListSerializer` to use `get_dynamic_status_display()`
2. Removed status override logic in dashboard view

**Files Changed:**
- `leaves/serializers.py` - Line 221: Changed `source='get_status_display'` to `source='get_dynamic_status_display'`
- `leaves/views.py` - Lines 551-558: Removed stage_label override logic

**Results:**
- ✅ Merban Staff (pending): "Pending Manager Approval"
- ✅ Merban Manager (pending): "Pending HR Approval"
- ✅ Merban HR (pending): "Pending HR Approval"
- ✅ SDSL/SBL Staff (pending): "Pending CEO Approval"
- ✅ SDSL/SBL CEO (pending): "Pending HR Approval"

## Status Display Rules (Complete)

### "Pending Manager Approval" - Only for:
- Merban Capital staff (non-manager, non-HR, non-CEO) requesting leave

### "Pending HR Approval" - For:
- Merban managers requesting leave (goes to HR for approval)
- Merban HR requesting leave (self-approval at HR stage)
- SDSL/SBL CEOs requesting leave (skip CEO stage)
- All requests after manager/CEO approval

### "Pending CEO Approval" - For:
- SDSL/SBL staff/managers requesting leave (CEO approves first)
- Merban requests after HR approval

## Testing Verification

All workflows tested and verified:
- ✅ Manager request: status='pending', display='Pending HR Approval'
- ✅ HR request: status='pending', display='Pending HR Approval'
- ✅ Staff request: status='pending', display='Pending Manager Approval'
- ✅ CEO departments: All 3 CEOs have department=None
- ✅ Canonical departments: All 10 present in Merban Capital

## Files Modified
1. `leaves/serializers.py` - Updated LeaveRequestListSerializer.status_display
2. `leaves/views.py` - Removed stage_label override in dashboard view

## Database Changes
1. Deleted user: Eric Nartey (staff@sbl.com)
2. Deleted department: Executive (Merban Capital)
