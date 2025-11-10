#!/usr/bin/env python
import os
import sys
import django

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from leaves.models import LeaveRequest
from leaves.views import ManagerLeaveViewSet
from django.test import RequestFactory
from rest_framework.request import Request
from leaves.services import ApprovalWorkflowService

def debug_ceo_endpoint():
    print("🔍 Debug CEO Approvals Categorized Endpoint")
    print("=" * 60)
    
    # Get Benjamin (CEO)
    try:
        benjamin = CustomUser.objects.get(email='ceo@umbcapital.com')
        print(f"✅ CEO Found: {benjamin.username} ({benjamin.email})")
        print(f"   Role: {getattr(benjamin, 'role', 'Not set')}")
        print(f"   Affiliate: {getattr(benjamin, 'affiliate', 'Not set')}")
    except CustomUser.DoesNotExist:
        print("❌ Benjamin (CEO) not found")
        return
    
    print()
    
    # Create mock request
    factory = RequestFactory()
    http_request = factory.get('/leaves/manager/ceo_approvals_categorized/')
    http_request.user = benjamin
    
    # Create ViewSet instance
    viewset = ManagerLeaveViewSet()
    viewset.request = Request(http_request)
    viewset.format_kwarg = None
    
    print("🔍 Testing get_queryset() first:")
    queryset = viewset.get_queryset()
    print(f"   Base queryset count: {queryset.count()}")
    
    # Get candidate requests (same filter as endpoint)
    candidate_qs = queryset.filter(status__in=['pending', 'hr_approved']).exclude(employee__role='admin')
    print(f"   Candidate requests (pending/hr_approved, not admin): {candidate_qs.count()}")
    
    if candidate_qs.exists():
        print("\n📋 Candidate Requests:")
        for req in candidate_qs:
            employee = req.employee
            print(f"   • ID {req.id}: {employee.username} ({employee.email})")
            print(f"     Role: {getattr(employee, 'role', 'Not set')}")
            print(f"     Affiliate: {getattr(employee, 'affiliate', 'Not set')}")
            print(f"     Status: {req.status}")
    
    print()
    
    # Test ApprovalWorkflowService filtering
    print("🔍 Testing ApprovalWorkflowService filtering:")
    filtered_requests = []
    for req in candidate_qs:
        handler = ApprovalWorkflowService.get_handler(req)
        can_approve = handler.can_approve(benjamin, req.status)
        print(f"   • Request {req.id} (employee: {req.employee.username}, status: {req.status})")
        print(f"     Handler: {handler.__class__.__name__}")
        print(f"     Can CEO approve: {can_approve}")
        
        if can_approve:
            filtered_requests.append(req)
            print(f"     ✅ Added to filtered list")
        else:
            print(f"     ❌ Filtered out")
    
    print(f"\n📊 Final filtered requests: {len(filtered_requests)}")
    
    # Now test the actual endpoint method
    print("\n🎯 Testing actual ceo_approvals_categorized method:")
    
    try:
        response = viewset.ceo_approvals_categorized(viewset.request)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.data
            print(f"   Total Count: {data.get('total_count', 0)}")
            print(f"   Categories: {data.get('counts', {})}")
            
            categories = data.get('categories', {})
            for category, requests in categories.items():
                if requests:
                    print(f"\n   {category.upper()} Requests:")
                    for req_data in requests:
                        print(f"   • ID {req_data.get('id')}: {req_data.get('employee_name')} ({req_data.get('employee_email')})")
                        print(f"     Role: {req_data.get('employee_role')}")
                        print(f"     Status: {req_data.get('status')}")
        else:
            print(f"   Error: {response.data}")
            
    except Exception as e:
        print(f"   Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_ceo_endpoint()