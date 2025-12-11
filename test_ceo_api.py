#!/usr/bin/env python
"""Test CEO approval API endpoint directly"""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService
import json

User = get_user_model()

# Get pending requests
print("=" * 80)
print("TESTING CEO APPROVAL API")
print("=" * 80)

ceo = User.objects.get(email='ceo@umbcapital.com')
print(f"\nCEO: {ceo.get_full_name()} ({ceo.email})")
print(f"Affiliate: {ceo.affiliate.name if ceo.affiliate else 'None'}")

# Get leave requests in hr_approved status (Merban flow)
pending = LeaveRequest.objects.filter(status='hr_approved').select_related(
    'employee', 'employee__affiliate', 'employee__department', 'employee__department__affiliate'
)[:3]

print(f"\nTesting approval for {pending.count()} requests:")
for lr in pending:
    print(f"\n  LR#{lr.id} - {lr.employee.get_full_name()}")
    print(f"    Status: {lr.status}")
    print(f"    Employee Role: {lr.employee.role}")
    print(f"    Employee Dept: {lr.employee.department.name if lr.employee.department else 'None'}")
    
    can_approve = ApprovalWorkflowService.can_user_approve(lr, ceo)
    print(f"    Can CEO approve: {can_approve}")
    
    if can_approve:
        try:
            # Try to approve
            ApprovalWorkflowService.approve_request(lr, ceo, "Test approval")
            print(f"    ✓ APPROVAL SUCCESS - new status: {lr.status}")
            
            # Rollback
            lr.refresh_from_db()
            
        except Exception as e:
            print(f"    ✗ APPROVAL FAILED: {e}")

# Test API endpoint response format
print(f"\n{'='*80}")
print("TESTING API RESPONSE FORMAT")
print(f"{'='*80}")

from leaves.views import ManagerLeaveViewSet
from rest_framework.test import APIRequestFactory, force_authenticate

factory = APIRequestFactory()
request = factory.get('/api/leaves/manager/ceo_approvals_categorized/')
force_authenticate(request, user=ceo)
request.user = ceo  # Explicitly set user

viewset = ManagerLeaveViewSet.as_view({'get': 'ceo_approvals_categorized'})

try:
    response = viewset(request)
    data = response.data
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Total Count: {data.get('total_count')}")
    print(f"Counts: {data.get('counts')}")
    
    # Check one request from each category
    for cat_name, requests in data.get('categories', {}).items():
        if requests:
            print(f"\n{cat_name.upper()} Category (showing first request):")
            req = requests[0]
            print(f"  Employee: {req.get('employee_name')}")
            print(f"  Role: {req.get('employee_role')}")
            print(f"  Department: {req.get('employee_department')}")
            print(f"  Affiliate: {req.get('employee_department_affiliate')}")
            break
            
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
