#!/usr/bin/env python3
"""
Verify HR queue logic and admin approval power issues
"""

import os
import django
import sys

# Setup Django
sys.path.append('/d/Desktop/Leave management')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.models import LeaveRequest
from users.models import CustomUser
from django.db.models import Q
from leaves.services import ApprovalWorkflowService

print("=== VERIFYING HR QUEUE AND ADMIN APPROVAL ===\n")

# Get key users
hr_user = CustomUser.objects.filter(role='hr').first()
sdsl_ceo = CustomUser.objects.filter(role='ceo', affiliate__name__iexact='SDSL').first()
sbl_ceo = CustomUser.objects.filter(role='ceo', affiliate__name__iexact='SBL').first()
merban_ceo = CustomUser.objects.filter(role='ceo', affiliate__name__iexact='MERBAN CAPITAL').first()

print("Key Users:")
print(f"  HR: {hr_user.email if hr_user else 'None'} - Affiliate: {hr_user.affiliate.name if hr_user and hr_user.affiliate else 'None'}")
print(f"  SDSL CEO: {sdsl_ceo.email if sdsl_ceo else 'None'}")
print(f"  SBL CEO: {sbl_ceo.email if sbl_ceo else 'None'}")
print(f"  Merban CEO: {merban_ceo.email if merban_ceo else 'None'}\n")

# Issue 1: CEO pending requests should appear in HR queue
print("=" * 60)
print("ISSUE 1: CEO Pending Requests in HR Queue")
print("=" * 60)

# Check if CEOs have pending requests
for ceo, affiliate_name in [(sdsl_ceo, 'SDSL'), (sbl_ceo, 'SBL'), (merban_ceo, 'MERBAN CAPITAL')]:
    if ceo:
        ceo_requests = LeaveRequest.objects.filter(employee=ceo, status='pending')
        print(f"\n{affiliate_name} CEO ({ceo.email}):")
        print(f"  Pending requests: {ceo_requests.count()}")
        
        if ceo_requests.exists():
            for req in ceo_requests:
                handler = ApprovalWorkflowService.get_handler(req)
                flow = handler.get_approval_flow()
                print(f"  Request {req.id}:")
                print(f"    Workflow: {flow}")
                print(f"    Expected: Should appear in HR queue")

# Current HR queue logic
print(f"\n\nCurrent HR Queue Logic:")
merban_filter = (
    Q(employee__department__affiliate__name__iexact='MERBAN CAPITAL') |
    Q(employee__affiliate__name__iexact='MERBAN CAPITAL')
)

# Merban staff manager_approved
merban_staff = LeaveRequest.objects.filter(
    status='manager_approved'
).filter(merban_filter).exclude(employee__role='admin')
print(f"  Merban staff manager_approved: {merban_staff.count()}")

# Merban manager/HOD/HR pending
merban_mgr_hod_hr = LeaveRequest.objects.filter(
    status='pending'
).filter(merban_filter).filter(
    employee__role__in=['manager', 'hod', 'hr']
).exclude(employee__role='admin')
print(f"  Merban manager/HOD/HR pending: {merban_mgr_hod_hr.count()}")

# ALL CEO-approved
all_ceo_approved = LeaveRequest.objects.filter(status='ceo_approved').exclude(employee__role='admin')
print(f"  All CEO-approved: {all_ceo_approved.count()}")

# Missing: SDSL/SBL CEO pending requests
sdsl_filter = (
    Q(employee__department__affiliate__name__iexact='SDSL') |
    Q(employee__affiliate__name__iexact='SDSL')
)
sbl_filter = (
    Q(employee__department__affiliate__name__iexact='SBL') |
    Q(employee__affiliate__name__iexact='SBL')
)

sdsl_ceo_pending = LeaveRequest.objects.filter(
    status='pending'
).filter(sdsl_filter).filter(employee__role='ceo')
print(f"  SDSL CEO pending (MISSING): {sdsl_ceo_pending.count()}")

sbl_ceo_pending = LeaveRequest.objects.filter(
    status='pending'
).filter(sbl_filter).filter(employee__role='ceo')
print(f"  SBL CEO pending (MISSING): {sbl_ceo_pending.count()}")

total_current = merban_staff.count() + merban_mgr_hod_hr.count() + all_ceo_approved.count()
total_should_be = total_current + sdsl_ceo_pending.count() + sbl_ceo_pending.count()
print(f"\n  Current HR queue total: {total_current}")
print(f"  Should be: {total_should_be}")

# Issue 2: Admin approval power
print(f"\n\n{'=' * 60}")
print("ISSUE 2: Admin Approval Power vs Regular Approvers")
print("=" * 60)

admin = CustomUser.objects.filter(role='admin').first()
if admin:
    print(f"\nAdmin user: {admin.email}")
    
    # Test with various request statuses
    test_requests = LeaveRequest.objects.filter(status__in=['pending', 'manager_approved', 'hr_approved'])[:3]
    
    if test_requests.exists():
        print(f"\nTesting {test_requests.count()} requests:")
        for req in test_requests:
            handler = ApprovalWorkflowService.get_handler(req)
            flow = handler.get_approval_flow()
            required_role = flow.get(req.status, 'none')
            
            print(f"\n  Request {req.id} ({req.employee.email}):")
            print(f"    Status: {req.status}")
            print(f"    Required role: {required_role}")
            
            # Check if admin can approve
            admin_can = handler.can_approve(admin, req.status)
            print(f"    Admin can approve: {admin_can}")
            
            # Check if actual approver can approve
            if required_role == 'hr' and hr_user:
                hr_can = handler.can_approve(hr_user, req.status)
                print(f"    HR can approve: {hr_can}")
                if admin_can and not hr_can:
                    print(f"    ⚠️  WARNING: Admin can approve but HR cannot!")
            elif required_role == 'ceo':
                # Get the correct CEO for this request
                correct_ceo = handler.get_next_approver(req.status)
                if correct_ceo:
                    ceo_can = handler.can_approve(correct_ceo, req.status)
                    print(f"    CEO ({correct_ceo.email}) can approve: {ceo_can}")
                    if admin_can and not ceo_can:
                        print(f"    ⚠️  WARNING: Admin can approve but CEO cannot!")
    else:
        print("  No test requests found")

print("\n=== VERIFICATION COMPLETE ===")
