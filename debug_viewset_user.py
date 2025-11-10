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
from django.db.models import Q

def debug_viewset_user():
    print("🔍 Debug ViewSet User Context")
    print("=" * 50)
    
    # Get Benjamin (CEO)
    benjamin = CustomUser.objects.get(email='ceo@umbcapital.com')
    print(f"✅ Original CEO: {benjamin.username}")
    print(f"   ID: {benjamin.id}")
    print(f"   Affiliate: {benjamin.affiliate}")
    print(f"   Role: {benjamin.role}")
    
    # Create proper request
    factory = RequestFactory()
    http_request = factory.get('/leaves/manager/ceo_approvals_categorized/')
    http_request.user = benjamin
    
    # Create ViewSet
    viewset = ManagerLeaveViewSet()
    viewset.request = Request(http_request)
    viewset.format_kwarg = None
    
    print()
    print("🔍 ViewSet Request User:")
    request_user = viewset.request.user
    print(f"   User: {request_user.username}")
    print(f"   ID: {request_user.id}")
    print(f"   Email: {request_user.email}")
    print(f"   Affiliate: {request_user.affiliate}")
    print(f"   Role: {getattr(request_user, 'role', 'Not set')}")
    print(f"   Same object: {benjamin == request_user}")
    print(f"   Same ID: {benjamin.id == request_user.id}")
    
    print()
    print("🔍 Manually calling get_queryset with debug:")
    
    # Let me patch the get_queryset method to add debug info
    original_get_queryset = viewset.get_queryset
    
    def debug_get_queryset():
        print("   📍 Inside get_queryset()")
        try:
            user = viewset.request.user
            print(f"   User in method: {user.username} (ID: {user.id})")
            print(f"   User affiliate: {user.affiliate}")
            print(f"   User role: {getattr(user, 'role', 'Not set')}")
            
            role = getattr(user, 'role', None)
            print(f"   Detected role: {role}")
            
            if role == 'ceo':
                print("   📍 In CEO branch")
                ceo_affiliate = user.affiliate
                print(f"   CEO affiliate: {ceo_affiliate}")
                
                if not ceo_affiliate:
                    print("   ❌ No affiliate - returning empty queryset")
                    return LeaveRequest.objects.none()
                
                # Get base queryset
                qs = LeaveRequest.objects.all()
                print(f"   Base queryset count: {qs.count()}")
                
                # Apply filters
                filtered_qs = qs.filter(
                    Q(employee__affiliate=ceo_affiliate) | Q(employee__department__affiliate=ceo_affiliate)
                ).filter(status__in=['pending', 'hr_approved', 'ceo_approved', 'approved', 'rejected'])
                
                print(f"   Filtered queryset count: {filtered_qs.count()}")
                
                if filtered_qs.exists():
                    for req in filtered_qs:
                        print(f"     • ID {req.id}: {req.employee.username} (status: {req.status})")
                
                return filtered_qs
            else:
                print(f"   📍 Not CEO role (role={role}) - calling original method")
                return original_get_queryset()
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            import traceback
            traceback.print_exc()
            return LeaveRequest.objects.none()
    
    # Replace the method temporarily
    viewset.get_queryset = debug_get_queryset
    
    # Now call it
    result = viewset.get_queryset()
    print(f"   Final result count: {result.count()}")

if __name__ == "__main__":
    debug_viewset_user()