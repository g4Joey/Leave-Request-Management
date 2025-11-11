#!/usr/bin/env python
"""Debug why LeaveRequestViewSet returns 0 requests for CEO."""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Affiliate
from leaves.models import LeaveRequest
from leaves.views import ManagerLeaveViewSet  # This is the correct viewset for CEO approvals
from django.test import RequestFactory
from django.db.models import Q

User = get_user_model()

def debug_ceo_queryset_step_by_step():
    """Step-by-step debugging of the CEO queryset logic."""
    print("=== DEBUG CEO QUERYSET STEP BY STEP ===")
    
    # Get Benjamin
    benjamin = User.objects.filter(email='ceo@umbcapital.com').first()
    if not benjamin:
        print("❌ Benjamin not found")
        return
    
    print(f"Benjamin: {benjamin.get_full_name()} ({benjamin.email})")
    print(f"Role: {benjamin.role}")
    print(f"Affiliate: {benjamin.affiliate}")
    print(f"Department: {benjamin.department}")
    
    # Create a mock request
    factory = RequestFactory()
    request = factory.get('/api/leaves/')
    request.user = benjamin
    
    # Create viewset instance
    viewset = ManagerLeaveViewSet()  # Use the correct viewset
    viewset.request = request
    
    # Manually step through the get_queryset logic
    print(f"\n--- Stepping through get_queryset() logic ---")
    
    user = request.user
    qs = LeaveRequest.objects.all()
    role = getattr(user, 'role', None)
    
    print(f"Initial queryset count: {qs.count()}")
    print(f"User role: {role}")
    
    # Check admin/superuser condition
    is_superuser = getattr(user, 'is_superuser', False)
    is_admin_role = role == 'admin'
    print(f"Is superuser: {is_superuser}")
    print(f"Is admin role: {is_admin_role}")
    
    if is_superuser or is_admin_role:
        print("❌ User would get full admin access - this shouldn't happen for CEO")
        return qs
    
    # Check CEO condition
    if role == 'ceo':
        print("✅ Role is CEO, applying CEO filtering...")
        
        ceo_affiliate = user.affiliate
        print(f"CEO affiliate: {ceo_affiliate}")
        
        if not ceo_affiliate:
            print("❌ CEO has no affiliate - would return empty queryset")
            return qs.none()
        
        # Apply the filtering step by step
        print(f"\n--- Applying CEO filters ---")
        
        # First filter: affiliate matching
        affiliate_filter = qs.filter(
            Q(employee__affiliate=ceo_affiliate) | Q(employee__department__affiliate=ceo_affiliate)
        )
        print(f"After affiliate filtering: {affiliate_filter.count()} requests")
        
        for req in affiliate_filter:
            print(f"  - Request {req.id}: {req.employee.get_full_name()}")
            print(f"    Employee affiliate: {req.employee.affiliate}")
            print(f"    Employee department: {req.employee.department}")
            print(f"    Employee dept affiliate: {req.employee.department.affiliate if req.employee.department else None}")
            print(f"    Status: {req.status}")
        
        # Second filter: status matching  
        status_filter = ['pending', 'hr_approved', 'ceo_approved', 'approved', 'rejected']
        final_qs = affiliate_filter.filter(status__in=status_filter)
        print(f"After status filtering ({status_filter}): {final_qs.count()} requests")
        
        for req in final_qs:
            print(f"  - Request {req.id}: {req.employee.get_full_name()} ({req.status})")
        
        return final_qs
    
    print(f"❌ Role '{role}' not handled by CEO logic")
    return qs.none()

def test_viewset_directly():
    """Test the actual viewset method call."""
    print(f"\n=== TESTING VIEWSET DIRECTLY ===")
    
    benjamin = User.objects.filter(email='ceo@umbcapital.com').first()
    if not benjamin:
        print("❌ Benjamin not found")
        return
    
    # Create a mock request
    factory = RequestFactory()
    request = factory.get('/api/leaves/')
    request.user = benjamin
    
    # Test the viewset
    viewset = ManagerLeaveViewSet()  # Use the correct viewset
    viewset.request = request
    viewset.format_kwarg = None  # Add this to avoid AttributeError
    viewset.action = 'list'      # Set the action
    
    try:
        queryset = viewset.get_queryset()
        print(f"Viewset.get_queryset() returned: {queryset.count()} requests")
        
        for req in queryset:
            print(f"  - Request {req.id}: {req.employee.get_full_name()} ({req.status})")
            
    except Exception as e:
        print(f"❌ Error calling viewset.get_queryset(): {e}")
        import traceback
        traceback.print_exc()

def check_augustine_request_details():
    """Check Augustine's specific request that should be visible."""
    print(f"\n=== CHECKING AUGUSTINE'S REQUEST DETAILS ===")
    
    augustine_req = LeaveRequest.objects.filter(employee__email__icontains='akorfu').first()
    if not augustine_req:
        print("❌ Augustine's request not found")
        return
    
    print(f"Augustine's request (ID {augustine_req.id}):")
    print(f"  Employee: {augustine_req.employee.get_full_name()}")
    print(f"  Employee email: {augustine_req.employee.email}")
    print(f"  Employee role: {augustine_req.employee.role}")
    print(f"  Employee affiliate: {augustine_req.employee.affiliate}")
    print(f"  Employee affiliate ID: {augustine_req.employee.affiliate.id if augustine_req.employee.affiliate else None}")
    print(f"  Employee department: {augustine_req.employee.department}")
    print(f"  Employee dept affiliate: {augustine_req.employee.department.affiliate if augustine_req.employee.department else None}")
    print(f"  Employee dept affiliate ID: {augustine_req.employee.department.affiliate.id if augustine_req.employee.department and augustine_req.employee.department.affiliate else None}")
    print(f"  Status: {augustine_req.status}")
    print(f"  Created: {augustine_req.created_at}")
    
    # Test if Benjamin should see this request
    benjamin = User.objects.filter(email='ceo@umbcapital.com').first()
    if benjamin and benjamin.affiliate:
        ben_affiliate = benjamin.affiliate
        print(f"\nBenjamin's affiliate: {ben_affiliate} (ID: {ben_affiliate.id})")
        
        # Test both conditions
        emp_affiliate_match = augustine_req.employee.affiliate == ben_affiliate
        emp_dept_affiliate_match = (
            augustine_req.employee.department and 
            augustine_req.employee.department.affiliate == ben_affiliate
        )
        
        print(f"  Employee affiliate matches Benjamin: {emp_affiliate_match}")
        print(f"  Employee dept affiliate matches Benjamin: {emp_dept_affiliate_match}")
        print(f"  Status in CEO viewable list: {augustine_req.status in ['pending', 'hr_approved', 'ceo_approved', 'approved', 'rejected']}")

def main():
    """Run all debugging steps."""
    print("DEBUGGING CEO QUERYSET ISSUE")
    print("=" * 50)
    
    debug_ceo_queryset_step_by_step()
    test_viewset_directly()
    check_augustine_request_details()

if __name__ == "__main__":
    main()