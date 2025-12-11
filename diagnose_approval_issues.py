#!/usr/bin/env python3
"""
Diagnose the approval workflow issues reported by the user
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

print("=== DIAGNOSING APPROVAL WORKFLOW ISSUES ===\n")

# Get key users
hr_user = CustomUser.objects.filter(role='hr').first()
manager = CustomUser.objects.filter(email='jmankoe@umbcapital.com').first()
admin = CustomUser.objects.filter(role='admin').first()
merban_ceo = CustomUser.objects.filter(role='ceo', affiliate__name__iexact='MERBAN CAPITAL').first()

print("Key Users:")
print(f"  HR: {hr_user.email if hr_user else 'None'} - Affiliate: {hr_user.affiliate.name if hr_user and hr_user.affiliate else 'None'}")
print(f"  Manager: {manager.email if manager else 'None'} - Affiliate: {manager.affiliate.name if manager and manager.affiliate else 'None'}")
print(f"  Admin: {admin.email if admin else 'None'}")
print(f"  Merban CEO: {merban_ceo.email if merban_ceo else 'None'}\n")

# Issue 1: HR's own leave request
print("=" * 60)
print("ISSUE 1: HR's Own Leave Request")
print("=" * 60)
if hr_user:
    hr_requests = LeaveRequest.objects.filter(employee=hr_user).order_by('-created_at')
    if hr_requests.exists():
        hr_req = hr_requests.first()
        print(f"HR Request ID: {hr_req.id}")
        print(f"  Status: {hr_req.status}")
        print(f"  Expected: Should be 'pending' with next approver = CEO (skip manager and HR)")
        print(f"  Display Status: {hr_req.get_status_display()}")
        
        # Check what the handler says
        handler = ApprovalWorkflowService.get_handler(hr_req)
        print(f"  Handler Type: {type(handler).__name__}")
        print(f"  Approval Flow: {handler.get_approval_flow()}")
        next_approver = handler.get_next_approver(hr_req.status)
        print(f"  Next Approver: {next_approver.email if next_approver else 'None'} ({next_approver.role if next_approver else 'N/A'})")
        print(f"  Problem: Status says '{hr_req.get_status_display()}' but should say 'Pending CEO Approval'")
        
        # Test dynamic status display
        print(f"\n  Dynamic Status Display Test:")
        print(f"    Old display: {hr_req.get_status_display()}")
        print(f"    New display: {hr_req.get_dynamic_status_display()}")
    else:
        print("  No HR requests found")
print()

# Issue 2: Manager's leave request
print("=" * 60)
print("ISSUE 2: Manager's (jmankoe) Leave Request")
print("=" * 60)
if manager:
    mgr_requests = LeaveRequest.objects.filter(employee=manager).order_by('-created_at')
    if mgr_requests.exists():
        mgr_req = mgr_requests.first()
        print(f"Manager Request ID: {mgr_req.id}")
        print(f"  Status: {mgr_req.status}")
        print(f"  Expected: Should be 'pending' routing to HR first, then CEO")
        print(f"  Display Status: {mgr_req.get_status_display()}")
        
        # Check what the handler says
        handler = ApprovalWorkflowService.get_handler(mgr_req)
        print(f"  Handler Type: {type(handler).__name__}")
        print(f"  Approval Flow: {handler.get_approval_flow()}")
        next_approver = handler.get_next_approver(mgr_req.status)
        print(f"  Next Approver: {next_approver.email if next_approver else 'None'} ({next_approver.role if next_approver else 'N/A'})")
        print(f"  Problem: Should show in HR approval queue, not CEO queue")
        
        # Check where it's showing
        print(f"\n  Checking visibility in queues:")
        
        # HR queue (Merban staff manager_approved + Merban manager/HOD/HR pending + all ceo_approved)
        in_hr_queue_staff = LeaveRequest.objects.filter(
            Q(employee__department__affiliate__name__iexact='MERBAN CAPITAL') |
            Q(employee__affiliate__name__iexact='MERBAN CAPITAL')
        ).filter(status='manager_approved', id=mgr_req.id).exists()
        
        in_hr_queue_mgr_hod_hr = LeaveRequest.objects.filter(
            Q(employee__department__affiliate__name__iexact='MERBAN CAPITAL') |
            Q(employee__affiliate__name__iexact='MERBAN CAPITAL')
        ).filter(status='pending', employee__role__in=['manager', 'hod', 'hr'], id=mgr_req.id).exists()
        
        print(f"    In HR queue (staff manager_approved): {in_hr_queue_staff}")
        print(f"    In HR queue (manager/HOD/HR pending): {in_hr_queue_mgr_hod_hr}")
        
        # CEO queue (should see if status='pending' or 'hr_approved' and handler.can_approve)
        if merban_ceo:
            can_ceo_approve = handler.can_approve(merban_ceo, mgr_req.status)
            print(f"    Merban CEO can approve: {can_ceo_approve}")
        
        # Admin CEO queue
        if admin:
            can_admin_approve = handler.can_approve(admin, mgr_req.status)
            required_role_at_this_stage = handler.get_approval_flow().get(mgr_req.status)
            print(f"    Admin can approve at current stage ({required_role_at_this_stage}): {can_admin_approve}")
        
        # Test dynamic status display
        print(f"\n  Dynamic Status Display Test:")
        print(f"    Old display: {mgr_req.get_status_display()}")
        print(f"    New display: {mgr_req.get_dynamic_status_display()}")
    else:
        print("  No manager requests found")
print()

# Issue 3: Admin counts vs actual items
print("=" * 60)
print("ISSUE 3: Admin Approval Counts")
print("=" * 60)
if admin:
    # Manager queue count for admin
    admin_mgr_queue = (
        LeaveRequest.objects
        .filter(status='pending')
        .exclude(employee__role__in=['manager', 'hr', 'ceo', 'admin'])
        .exclude(
            Q(employee__department__affiliate__name__iexact='SDSL') |
            Q(employee__department__affiliate__name__iexact='SBL') |
            Q(employee__affiliate__name__iexact='SDSL') |
            Q(employee__affiliate__name__iexact='SBL')
        )
    )
    print(f"Admin Manager Queue Count: {admin_mgr_queue.count()}")
    if admin_mgr_queue.exists():
        print("  Items:")
        for req in admin_mgr_queue:
            print(f"    - {req.employee.email} ({req.employee.role})")
    
    # HR queue count for admin
    merban_filter = (
        Q(employee__department__affiliate__name__iexact='MERBAN CAPITAL') |
        Q(employee__affiliate__name__iexact='MERBAN CAPITAL')
    )
    # Staff requests that are manager_approved
    admin_hr_staff = (
        LeaveRequest.objects
        .filter(status='manager_approved')
        .filter(merban_filter)
        .exclude(employee__role='admin')
    )
    # Manager/HOD/HR pending requests (skip-manager flow)
    admin_hr_mgr_hod_hr = (
        LeaveRequest.objects
        .filter(status='pending')
        .filter(merban_filter)
        .filter(employee__role__in=['manager', 'hod', 'hr'])
        .exclude(employee__role='admin')
    )
    # CEO-approved requests (all affiliates)
    admin_hr_ceo_approved = LeaveRequest.objects.filter(status='ceo_approved').exclude(employee__role='admin')
    
    print(f"\nAdmin HR Queue:")
    print(f"  Merban staff manager_approved: {admin_hr_staff.count()}")
    if admin_hr_staff.exists():
        for req in admin_hr_staff:
            print(f"    - {req.employee.email} ({req.employee.role})")
    print(f"  Merban manager/HOD/HR pending: {admin_hr_mgr_hod_hr.count()}")
    if admin_hr_mgr_hod_hr.exists():
        for req in admin_hr_mgr_hod_hr:
            print(f"    - {req.employee.email} ({req.employee.role})")
    print(f"  CEO approved (all affiliates): {admin_hr_ceo_approved.count()}")
    if admin_hr_ceo_approved.exists():
        for req in admin_hr_ceo_approved:
            print(f"    - {req.employee.email} ({req.employee.role})")
    print(f"  Total HR queue: {admin_hr_staff.count() + admin_hr_mgr_hod_hr.count() + admin_hr_ceo_approved.count()}")
    
    # CEO queue count for admin
    admin_ceo_queue = LeaveRequest.objects.filter(status='hr_approved')
    print(f"\nAdmin CEO Queue Count: {admin_ceo_queue.count()}")
    if admin_ceo_queue.exists():
        print("  Items:")
        for req in admin_ceo_queue:
            print(f"    - {req.employee.email} ({req.employee.role})")

print("\n=== DIAGNOSIS COMPLETE ===")
