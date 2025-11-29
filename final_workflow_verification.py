#!/usr/bin/env python3
"""
Final verification of all workflow requirements
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
from leaves.services import ApprovalWorkflowService
from django.db.models import Q

print("=== FINAL WORKFLOW VERIFICATION ===\n")

# Get all key users
hr_user = CustomUser.objects.filter(role='hr').first()
sdsl_ceo = CustomUser.objects.filter(role='ceo', affiliate__name__iexact='SDSL').first()
sbl_ceo = CustomUser.objects.filter(role='ceo', affiliate__name__iexact='SBL').first()
merban_ceo = CustomUser.objects.filter(role='ceo', affiliate__name__iexact='MERBAN CAPITAL').first()
manager = CustomUser.objects.filter(email='jmankoe@umbcapital.com').first()
admin = CustomUser.objects.filter(role='admin').first()

print("=" * 70)
print("REQUIREMENT 1: HR Queue for Merban Capital")
print("=" * 70)
print("Expected:")
print("  - Manager-approved staff requests")
print("  - Pending requests from managers themselves")
print("  - Pending requests from HR (HR goes to CEO)")
print()

merban_filter = (
    Q(employee__department__affiliate__name__iexact='MERBAN CAPITAL') |
    Q(employee__affiliate__name__iexact='MERBAN CAPITAL')
)

# Check manager-approved staff
merban_staff = LeaveRequest.objects.filter(
    status='manager_approved'
).filter(merban_filter).exclude(employee__role='admin')
print(f"✓ Merban staff manager_approved: {merban_staff.count()}")

# Check manager/HOD/HR pending
merban_mgr_hod_hr = LeaveRequest.objects.filter(
    status='pending'
).filter(merban_filter).filter(employee__role__in=['manager', 'hod', 'hr'])
print(f"✓ Merban manager/HOD/HR pending: {merban_mgr_hod_hr.count()}")
for req in merban_mgr_hod_hr:
    handler = ApprovalWorkflowService.get_handler(req)
    flow = handler.get_approval_flow()
    next_role = flow.get('pending', 'none')
    print(f"  - {req.employee.email} ({req.employee.role}): next approver role = {next_role}")

print()
print("=" * 70)
print("REQUIREMENT 2: HR Queue for SDSL")
print("=" * 70)
print("Expected:")
print("  - CEO-approved staff requests")
print("  - Pending requests from SDSL CEO (CEO goes directly to HR)")
print()

sdsl_filter = (
    Q(employee__department__affiliate__name__iexact='SDSL') |
    Q(employee__affiliate__name__iexact='SDSL')
)

# Check SDSL staff CEO-approved
sdsl_ceo_approved = LeaveRequest.objects.filter(
    status='ceo_approved'
).filter(sdsl_filter).exclude(employee__role='admin')
print(f"✓ SDSL staff ceo_approved: {sdsl_ceo_approved.count()}")

# Check SDSL CEO pending
sdsl_ceo_pending = LeaveRequest.objects.filter(
    status='pending'
).filter(sdsl_filter).filter(employee__role='ceo')
print(f"✓ SDSL CEO pending: {sdsl_ceo_pending.count()}")
for req in sdsl_ceo_pending:
    handler = ApprovalWorkflowService.get_handler(req)
    flow = handler.get_approval_flow()
    next_role = flow.get('pending', 'none')
    can_hr_approve = handler.can_approve(hr_user, req.status) if hr_user else False
    print(f"  - {req.employee.email}: next approver = {next_role}, HR can approve = {can_hr_approve}")

print()
print("=" * 70)
print("REQUIREMENT 3: HR Queue for SBL")
print("=" * 70)
print("Expected:")
print("  - CEO-approved staff requests")
print("  - Pending requests from SBL CEO (CEO goes directly to HR)")
print()

sbl_filter = (
    Q(employee__department__affiliate__name__iexact='SBL') |
    Q(employee__affiliate__name__iexact='SBL')
)

# Check SBL staff CEO-approved
sbl_ceo_approved = LeaveRequest.objects.filter(
    status='ceo_approved'
).filter(sbl_filter).exclude(employee__role='admin')
print(f"✓ SBL staff ceo_approved: {sbl_ceo_approved.count()}")

# Check SBL CEO pending
sbl_ceo_pending = LeaveRequest.objects.filter(
    status='pending'
).filter(sbl_filter).filter(employee__role='ceo')
print(f"✓ SBL CEO pending: {sbl_ceo_pending.count()}")
for req in sbl_ceo_pending:
    handler = ApprovalWorkflowService.get_handler(req)
    flow = handler.get_approval_flow()
    next_role = flow.get('pending', 'none')
    can_hr_approve = handler.can_approve(hr_user, req.status) if hr_user else False
    print(f"  - {req.employee.email}: next approver = {next_role}, HR can approve = {can_hr_approve}")

print()
print("=" * 70)
print("REQUIREMENT 4: Admin Approval Power Does NOT Block Regular Approvers")
print("=" * 70)

if admin and hr_user:
    # Test with HR queue items
    test_requests = LeaveRequest.objects.filter(
        Q(status='pending', employee__role='manager') |
        Q(status='pending', employee__role='ceo', employee__affiliate__name__in=['SDSL', 'SBL'])
    )[:3]
    
    print(f"Testing {test_requests.count()} requests:\n")
    all_pass = True
    for req in test_requests:
        handler = ApprovalWorkflowService.get_handler(req)
        flow = handler.get_approval_flow()
        required_role = flow.get(req.status, 'none')
        
        admin_can = handler.can_approve(admin, req.status)
        hr_can = handler.can_approve(hr_user, req.status)
        
        # HR should be able to approve if required_role is 'hr'
        expected_hr_can = (required_role == 'hr')
        
        status_symbol = "✓" if hr_can == expected_hr_can else "✗"
        print(f"{status_symbol} Request {req.id} ({req.employee.email} - {req.employee.role}):")
        print(f"  Required role: {required_role}")
        print(f"  Admin can approve: {admin_can}")
        print(f"  HR can approve: {hr_can} (expected: {expected_hr_can})")
        
        if admin_can and expected_hr_can and not hr_can:
            print(f"  ✗ FAIL: Admin can approve but designated HR approver cannot!")
            all_pass = False
    
    if all_pass:
        print(f"\n✅ PASS: Admin does not block regular approvers")
    else:
        print(f"\n❌ FAIL: Some issues found")
else:
    print("  ⚠ Cannot test - admin or HR user not found")

print()
print("=" * 70)
print("WORKFLOW SUMMARY")
print("=" * 70)
print()
print("Merban Capital:")
print("  Staff:        Manager → HR → CEO")
print("  Manager/HOD:  HR → CEO")
print("  HR:           CEO (final)")
print("  CEO:          Does not request leave")
print()
print("SDSL:")
print("  Staff:        CEO → HR (final)")
print("  CEO:          HR (final)")
print()
print("SBL:")
print("  Staff:        CEO → HR (final)")
print("  CEO:          HR (final)")

print()
print("=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
