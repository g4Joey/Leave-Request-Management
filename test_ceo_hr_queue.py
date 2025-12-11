#!/usr/bin/env python3
"""
Test the updated HR queue logic with CEO requests
"""

import os
import django
import sys

# Setup Django
sys.path.append('/d/Desktop/Leave management')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.models import LeaveRequest, LeaveType
from users.models import CustomUser
from datetime import date, timedelta
from leaves.services import ApprovalWorkflowService
from django.db.models import Q

print("=== TESTING UPDATED HR QUEUE LOGIC ===\n")

# Get users
hr_user = CustomUser.objects.filter(role='hr').first()
sdsl_ceo = CustomUser.objects.filter(role='ceo', affiliate__name__iexact='SDSL').first()
sbl_ceo = CustomUser.objects.filter(role='ceo', affiliate__name__iexact='SBL').first()
merban_ceo = CustomUser.objects.filter(role='ceo', affiliate__name__iexact='MERBAN CAPITAL').first()

print("Key Users:")
print(f"  HR: {hr_user.email if hr_user else 'None'}")
print(f"  SDSL CEO: {sdsl_ceo.email if sdsl_ceo else 'None'}")
print(f"  SBL CEO: {sbl_ceo.email if sbl_ceo else 'None'}")
print(f"  Merban CEO: {merban_ceo.email if merban_ceo else 'None'}\n")

# Get leave type
leave_type = LeaveType.objects.filter(is_active=True).first()
if not leave_type:
    print("❌ No active leave type found")
    exit(1)

# Clean up existing CEO test requests
print("Cleaning up existing CEO test requests...")
LeaveRequest.objects.filter(
    employee__role='ceo',
    employee__email__in=['sdslceo@umbcapital.com', 'sblceo@umbcapital.com', 'ceo@umbcapital.com']
).delete()

# Create test CEO requests
print("\n=== Creating Test CEO Requests ===")
ceo_requests = []

if sdsl_ceo:
    try:
        sdsl_req = LeaveRequest.objects.create(
            employee=sdsl_ceo,
            leave_type=leave_type,
            start_date=date.today() + timedelta(days=20),
            end_date=date.today() + timedelta(days=22),
            total_days=3,
            reason="SDSL CEO test request"
        )
        print(f"✅ Created SDSL CEO request: {sdsl_req.id}")
        ceo_requests.append(('SDSL', sdsl_req))
    except Exception as e:
        print(f"❌ Failed to create SDSL CEO request: {e}")

if sbl_ceo:
    try:
        sbl_req = LeaveRequest.objects.create(
            employee=sbl_ceo,
            leave_type=leave_type,
            start_date=date.today() + timedelta(days=25),
            end_date=date.today() + timedelta(days=27),
            total_days=3,
            reason="SBL CEO test request"
        )
        print(f"✅ Created SBL CEO request: {sbl_req.id}")
        ceo_requests.append(('SBL', sbl_req))
    except Exception as e:
        print(f"❌ Failed to create SBL CEO request: {e}")

if merban_ceo:
    try:
        merban_req = LeaveRequest.objects.create(
            employee=merban_ceo,
            leave_type=leave_type,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=32),
            total_days=3,
            reason="Merban CEO test request"
        )
        print(f"✅ Created Merban CEO request: {merban_req.id}")
        ceo_requests.append(('MERBAN', merban_req))
    except Exception as e:
        print(f"❌ Failed to create Merban CEO request: {e}")

# Test workflows for each CEO request
print("\n=== Testing CEO Request Workflows ===")
for affiliate, req in ceo_requests:
    print(f"\n{affiliate} CEO Request (ID: {req.id}):")
    handler = ApprovalWorkflowService.get_handler(req)
    flow = handler.get_approval_flow()
    next_approver = handler.get_next_approver(req.status)
    
    print(f"  Status: {req.status}")
    print(f"  Workflow: {flow}")
    print(f"  Next Approver: {next_approver.email if next_approver else 'None'} ({next_approver.role if next_approver else 'N/A'})")
    print(f"  Dynamic Status: {req.get_dynamic_status_display()}")
    print(f"  Expected: Should go to HR (skip CEO stage)")
    
    if hr_user:
        can_hr_approve = handler.can_approve(hr_user, req.status)
        print(f"  HR can approve: {can_hr_approve}")

# Test HR queue visibility
print("\n\n=== Testing HR Queue Visibility ===")

# Build filters
merban_filter = (
    Q(employee__department__affiliate__name__iexact='MERBAN CAPITAL') |
    Q(employee__affiliate__name__iexact='MERBAN CAPITAL')
)
sdsl_filter = (
    Q(employee__department__affiliate__name__iexact='SDSL') |
    Q(employee__affiliate__name__iexact='SDSL')
)
sbl_filter = (
    Q(employee__department__affiliate__name__iexact='SBL') |
    Q(employee__affiliate__name__iexact='SBL')
)

# Check each component of HR queue
print("\nHR Queue Components:")

# 1. Merban staff manager_approved
merban_staff = LeaveRequest.objects.filter(
    status='manager_approved'
).filter(merban_filter).exclude(employee__role='admin')
print(f"  1. Merban staff manager_approved: {merban_staff.count()}")

# 2. Merban manager/HOD/HR pending
merban_mgr = LeaveRequest.objects.filter(
    status='pending'
).filter(merban_filter).filter(employee__role__in=['manager', 'hod', 'hr'])
print(f"  2. Merban manager/HOD/HR pending: {merban_mgr.count()}")
for req in merban_mgr:
    print(f"     - {req.employee.email} ({req.employee.role})")

# 3. SDSL/SBL staff CEO-approved
sdsl_sbl_ceo_approved = LeaveRequest.objects.filter(
    status='ceo_approved'
).filter(sdsl_filter | sbl_filter).exclude(employee__role='admin')
print(f"  3. SDSL/SBL staff ceo_approved: {sdsl_sbl_ceo_approved.count()}")

# 4. SDSL CEO pending
sdsl_ceo_pending = LeaveRequest.objects.filter(
    status='pending'
).filter(sdsl_filter).filter(employee__role='ceo')
print(f"  4. SDSL CEO pending: {sdsl_ceo_pending.count()}")
for req in sdsl_ceo_pending:
    print(f"     - {req.employee.email}")

# 5. SBL CEO pending
sbl_ceo_pending = LeaveRequest.objects.filter(
    status='pending'
).filter(sbl_filter).filter(employee__role='ceo')
print(f"  5. SBL CEO pending: {sbl_ceo_pending.count()}")
for req in sbl_ceo_pending:
    print(f"     - {req.employee.email}")

total_hr_queue = (
    merban_staff.count() + 
    merban_mgr.count() + 
    sdsl_sbl_ceo_approved.count() +
    sdsl_ceo_pending.count() +
    sbl_ceo_pending.count()
)
print(f"\n  Total HR Queue: {total_hr_queue}")

# Verify admin doesn't block approvals
print("\n\n=== Verifying Admin Doesn't Block Approvals ===")
admin = CustomUser.objects.filter(role='admin').first()
if admin and hr_user and ceo_requests:
    test_req = ceo_requests[0][1]  # Get first CEO request
    handler = ApprovalWorkflowService.get_handler(test_req)
    
    admin_can = handler.can_approve(admin, test_req.status)
    hr_can = handler.can_approve(hr_user, test_req.status)
    
    print(f"Test Request: {test_req.employee.email} (ID: {test_req.id})")
    print(f"  Admin can approve: {admin_can}")
    print(f"  HR can approve: {hr_can}")
    
    if admin_can and hr_can:
        print(f"  ✅ PASS: Both admin and HR can approve (admin doesn't block)")
    elif not hr_can:
        print(f"  ❌ FAIL: HR cannot approve!")
    else:
        print(f"  ✅ PASS: HR can approve")

print("\n=== TEST COMPLETE ===")
