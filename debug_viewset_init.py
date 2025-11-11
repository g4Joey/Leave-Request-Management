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

def debug_viewset_differences():
    print("🔍 Debug ViewSet Initialization Differences")
    print("=" * 60)
    
    # Get Benjamin (CEO)
    benjamin = CustomUser.objects.get(email='ceo@umbcapital.com')
    print(f"✅ CEO: {benjamin.username} (role: {benjamin.role})")
    print(f"   Affiliate: {benjamin.affiliate}")
    print(f"   Is superuser: {benjamin.is_superuser}")
    print(f"   Role check: user_role = getattr(user, 'role', None) = {getattr(benjamin, 'role', None)}")
    
    print()
    
    # Test 1: ViewSet without request (like our earlier test)
    print("🔍 Test 1: ViewSet without request context")
    viewset1 = ManagerLeaveViewSet()
    try:
        # Manually set the user for filtering
        viewset1._current_user = benjamin
        queryset1 = viewset1.get_queryset()
        print(f"   Queryset count: {queryset1.count()}")
        if queryset1.exists():
            for req in queryset1:
                print(f"   • Request {req.id}: {req.employee.username} (status: {req.status})")
    except Exception as e:
        print(f"   Error: {e}")
    
    print()
    
    # Test 2: ViewSet with proper request context
    print("🔍 Test 2: ViewSet with request context")
    factory = RequestFactory()
    http_request = factory.get('/leaves/manager/ceo_approvals_categorized/')
    http_request.user = benjamin
    
    viewset2 = ManagerLeaveViewSet()
    viewset2.request = Request(http_request)
    viewset2.format_kwarg = None
    
    try:
        queryset2 = viewset2.get_queryset()
        print(f"   Queryset count: {queryset2.count()}")
        if queryset2.exists():
            for req in queryset2:
                print(f"   • Request {req.id}: {req.employee.username} (status: {req.status})")
    except Exception as e:
        print(f"   Error: {e}")
    
    print()
    
    # Test 3: Check role validation
    print("🔍 Test 3: Role validation check")
    user = benjamin
    user_role = getattr(user, 'role', None)
    is_superuser = getattr(user, 'is_superuser', False)
    
    print(f"   user_role: {repr(user_role)}")
    print(f"   is_superuser: {is_superuser}")
    print(f"   user_role != 'ceo': {user_role != 'ceo'}")
    print(f"   not is_superuser: {not is_superuser}")
    print(f"   Full condition: {user_role != 'ceo' and not is_superuser}")
    
    if user_role != 'ceo' and not is_superuser:
        print("   ❌ Would be rejected")
    else:
        print("   ✅ Should be allowed")

    print()
    
    # Test 4: Check all HR approved requests
    print("🔍 Test 4: All HR approved requests in system")
    all_hr_approved = LeaveRequest.objects.filter(status='hr_approved')
    print(f"   Total hr_approved requests: {all_hr_approved.count()}")
    
    for req in all_hr_approved:
        print(f"   • Request {req.id}: {req.employee.username} ({req.employee.email})")
        print(f"     Employee role: {getattr(req.employee, 'role', 'Not set')}")
        print(f"     Employee affiliate: {getattr(req.employee, 'affiliate', 'Not set')}")
        print(f"     Status: {req.status}")

if __name__ == "__main__":
    debug_viewset_differences()