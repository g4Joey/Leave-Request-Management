#!/usr/bin/env python
"""Direct Django test of HR approvals categorization"""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from leaves.models import LeaveRequest
from leaves.views import ManagerLeaveViewSet
from leaves.services import ApprovalWorkflowService, ApprovalRoutingService
from rest_framework.test import APIRequestFactory, force_authenticate

User = get_user_model()

# Get HR user
hr_user = User.objects.filter(role='hr', is_active=True).first()
print(f"HR User: {hr_user.email}\n")

# Create request
factory = APIRequestFactory()
request = factory.get('/api/leaves/manager/hr_approvals_categorized/')
force_authenticate(request, user=hr_user)
request.user = hr_user

# Call the view
viewset = ManagerLeaveViewSet.as_view({'get': 'hr_approvals_categorized'})
response = viewset(request)

print("="*80)
print("HR APPROVALS CATEGORIZED RESPONSE")
print("="*80)
print(f"Status Code: {response.status_code}\n")

if response.status_code == 200:
    data = response.data
    for affiliate, requests in data.get('groups', {}).items():
        print(f"{affiliate}: {len(requests)} requests")
        for req in requests:
            print(f"  LR#{req['id']}: {req['employee_name']} - {req['status']}")
    
    print(f"\nCounts: {data.get('counts')}")
    print(f"Total: {data.get('total')}")
else:
    print(f"Error: {response.data}")

# Now check what the queryset returns
print("\n" + "="*80)
print("DEBUGGING: Check candidate_qs directly")
print("="*80)

viewset_instance = ManagerLeaveViewSet()
viewset_instance.request = request
viewset_instance.format_kwarg = None

# Get the queryset (this applies get_queryset filters)
qs = viewset_instance.get_queryset()
print(f"Total queryset count: {qs.count()}")

# Filter for candidates
candidate_qs = qs.filter(status__in=['manager_approved', 'ceo_approved'])
print(f"Candidate requests (manager_approved or ceo_approved): {candidate_qs.count()}\n")

for req in candidate_qs:
    emp = req.employee
    aff_name = ApprovalRoutingService.get_employee_affiliate_name(emp)
    can_approve = ApprovalWorkflowService.can_user_approve(req, hr_user)
    print(f"LR#{req.id}: {emp.get_full_name()} - {aff_name} - {req.status} - Can approve: {can_approve}")
