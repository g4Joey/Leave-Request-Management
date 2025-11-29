#!/usr/bin/env python
"""Test HR approvals categorization for SDSL/SBL"""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService, ApprovalRoutingService
from datetime import datetime, timedelta

User = get_user_model()

print("=" * 80)
print("TESTING HR APPROVALS CATEGORIZATION FOR SDSL/SBL")
print("=" * 80)

# Get HR user
hr_user = User.objects.filter(role='hr', is_active=True).first()
if not hr_user:
    print("❌ No HR user found")
    exit(1)

print(f"\nHR User: {hr_user.get_full_name()} ({hr_user.email})")

# Check for ceo_approved requests from SDSL/SBL
print("\n" + "=" * 80)
print("CEO-APPROVED REQUESTS (should be pending HR approval for SDSL/SBL)")
print("=" * 80)

ceo_approved = LeaveRequest.objects.filter(status='ceo_approved').select_related(
    'employee', 'employee__affiliate', 'employee__department'
)

print(f"\nTotal ceo_approved requests: {ceo_approved.count()}")

for lr in ceo_approved:
    emp = lr.employee
    aff_name = ApprovalRoutingService.get_employee_affiliate_name(emp)
    can_approve = ApprovalWorkflowService.can_user_approve(lr, hr_user)
    
    print(f"\nLR#{lr.id}:")
    print(f"  Employee: {emp.get_full_name()}")
    print(f"  Affiliate: {aff_name}")
    print(f"  Employee Affiliate Object: {emp.affiliate.name if emp.affiliate else 'None'}")
    print(f"  Status: {lr.status}")
    print(f"  Can HR approve: {can_approve}")
    
    # Get handler and flow
    handler = ApprovalWorkflowService.get_handler(lr)
    flow = handler.get_approval_flow()
    print(f"  Handler: {handler.__class__.__name__}")
    print(f"  Approval flow: {flow}")
    print(f"  Required role for 'ceo_approved': {flow.get('ceo_approved')}")

# Check manager_approved from all affiliates
print("\n" + "=" * 80)
print("MANAGER-APPROVED REQUESTS (should be pending HR approval)")
print("=" * 80)

mgr_approved = LeaveRequest.objects.filter(status='manager_approved').select_related(
    'employee', 'employee__affiliate', 'employee__department'
)[:5]

for lr in mgr_approved:
    emp = lr.employee
    aff_name = ApprovalRoutingService.get_employee_affiliate_name(emp)
    can_approve = ApprovalWorkflowService.can_user_approve(lr, hr_user)
    
    print(f"\nLR#{lr.id}: {emp.get_full_name()} ({aff_name}) - Can HR approve: {can_approve}")
