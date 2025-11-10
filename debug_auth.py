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
from rest_framework.test import APIRequestFactory
from django.contrib.auth import authenticate
from django.db.models import Q

def debug_authentication():
    print("🔍 Debug Authentication Issue")
    print("=" * 50)
    
    # Get Benjamin (CEO)
    benjamin = CustomUser.objects.get(email='ceo@umbcapital.com')
    print(f"✅ CEO: {benjamin.username} (ID: {benjamin.id})")
    
    # Try different request creation methods
    
    print()
    print("🔍 Method 1: Basic RequestFactory")
    factory = RequestFactory()
    http_request = factory.get('/leaves/manager/ceo_approvals_categorized/')
    http_request.user = benjamin
    request = Request(http_request)
    print(f"   Request user: {request.user}")
    print(f"   Request user type: {type(request.user)}")
    print(f"   Is authenticated: {request.user.is_authenticated}")
    
    print()
    print("🔍 Method 2: Direct user assignment")
    factory2 = RequestFactory()
    http_req2 = factory2.get('/leaves/manager/ceo_approvals_categorized/')
    http_req2.user = benjamin
    request2 = Request(http_req2)
    request2.user = benjamin  # Force user on DRF request too
    print(f"   Request user: {request2.user}")
    print(f"   Request user type: {type(request2.user)}")
    print(f"   Is authenticated: {request2.user.is_authenticated}")
    
    print()
    print("🔍 Method 3: Using APIRequestFactory properly")
    api_factory = APIRequestFactory()
    api_req = api_factory.get('/leaves/manager/ceo_approvals_categorized/')
    # Create DRF request and force authentication
    drf_request = Request(api_req)
    drf_request.user = benjamin
    drf_request._user = benjamin
    drf_request._authenticator = None
    print(f"   DRF Request user: {drf_request.user}")
    print(f"   DRF Request user type: {type(drf_request.user)}")
    print(f"   Is authenticated: {drf_request.user.is_authenticated}")
    
    print()
    print("🔍 Testing ViewSet with Method 3:")
    viewset = ManagerLeaveViewSet()
    viewset.request = drf_request
    viewset.format_kwarg = None
    
    print(f"   ViewSet request user: {viewset.request.user}")
    print(f"   ViewSet request user type: {type(viewset.request.user)}")
    print(f"   ViewSet user is authenticated: {viewset.request.user.is_authenticated}")
    
    if viewset.request.user.is_authenticated:
        print(f"   User details: {viewset.request.user.username} (ID: {viewset.request.user.id})")
        print(f"   User role: {getattr(viewset.request.user, 'role', 'Not set')}")
        print(f"   User affiliate: {getattr(viewset.request.user, 'affiliate', 'Not set')}")
        
        # Now test get_queryset
        try:
            queryset = viewset.get_queryset()
            print(f"   Queryset count: {queryset.count()}")
            if queryset.exists():
                for req in queryset:
                    print(f"     • ID {req.id}: {req.employee.username} (status: {req.status})")
        except Exception as e:
            print(f"   Error in get_queryset: {e}")
            import traceback
            traceback.print_exc()
    
    print()
    print("🔍 Testing ceo_approvals_categorized method:")
    if viewset.request.user.is_authenticated:
        try:
            response = viewset.ceo_approvals_categorized(viewset.request)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.data
                print(f"   Total count: {data.get('total_count', 0)}")
                counts = data.get('counts', {})
                print(f"   Counts: {counts}")
            else:
                print(f"   Error: {response.data}")
        except Exception as e:
            print(f"   Exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_authentication()