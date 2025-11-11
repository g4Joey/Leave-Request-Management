#!/usr/bin/env python
"""Test CEO approval filtering and request visibility."""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser as User, Affiliate
from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService, ApprovalRoutingService
from django.db.models import Q

def test_ceo_approval_visibility():
    """Test what leave requests CEOs should see and approve."""
    print("=== CEO APPROVAL SYSTEM TEST ===")
    
    # Get all CEOs
    ceos = User.objects.filter(role='ceo', is_active=True).order_by('affiliate__name')
    
    for ceo in ceos:
        print(f"\n{ceo.get_full_name()} ({ceo.email}) - Affiliate: {ceo.affiliate}")
        
        # Get all leave requests from this CEO's affiliate
        affiliate = ceo.affiliate
        if not affiliate:
            print("  ERROR: CEO has no affiliate!")
            continue
            
        # Find employees under this affiliate
        employees = User.objects.filter(
            Q(affiliate=affiliate) | Q(department__affiliate=affiliate)
        ).exclude(id=ceo.id)  # Exclude the CEO themselves
        
        print(f"  Employees under {affiliate.name}: {employees.count()}")
        for emp in employees[:5]:  # Show first 5
            print(f"    - {emp.get_full_name()} ({emp.email}) - Role: {emp.role}")
            
        # Get leave requests from these employees
        leave_requests = LeaveRequest.objects.filter(employee__in=employees)
        print(f"  Leave requests from affiliate employees: {leave_requests.count()}")
        
        # Test approval routing for each request
        for req in leave_requests[:3]:  # Test first 3
            print(f"\n    Request ID {req.id}: {req.employee.get_full_name()} -> {req.leave_type} ({req.status})")
            
            # Test if this CEO should see this request
            expected_ceo = ApprovalRoutingService.get_ceo_for_employee(req.employee)
            print(f"      Expected CEO: {expected_ceo.get_full_name() if expected_ceo else None}")
            print(f"      Is correct CEO: {expected_ceo and expected_ceo.id == ceo.id}")
            
            # Test if CEO can approve
            can_approve = ApprovalWorkflowService.can_user_approve(req, ceo)
            print(f"      Can approve: {can_approve}")
            
            # Check what status would allow this CEO to approve
            handler = ApprovalWorkflowService.get_handler(req)
            flow = handler.get_approval_flow()
            print(f"      Approval flow: {flow}")
            
            # Find CEO's role in the flow
            ceo_statuses = [status for status, role in flow.items() if role == 'ceo']
            print(f"      CEO can approve at statuses: {ceo_statuses}")
            print(f"      Current status allows CEO: {req.status in ceo_statuses}")

def test_leave_request_filtering():
    """Test the actual leave request filtering that the view uses."""
    print("\n=== LEAVE REQUEST VIEW FILTERING TEST ===")
    
    # Simulate the filtering logic from LeaveRequestViewSet.get_queryset()
    from leaves.views import LeaveRequestViewSet
    
    ceos = User.objects.filter(role='ceo', is_active=True)
    
    for ceo in ceos:
        print(f"\n{ceo.get_full_name()} ({ceo.affiliate}) - CEO View Simulation:")
        
        # Simulate the get_queryset logic for CEO role
        # From line 632: return qs.filter(status__in=['pending', 'hr_approved', 'ceo_approved', 'approved', 'rejected'])
        qs = LeaveRequest.objects.all()
        
        # Apply CEO filtering
        ceo_requests = qs.filter(status__in=['pending', 'hr_approved', 'ceo_approved', 'approved', 'rejected'])
        print(f"  All requests in CEO-viewable statuses: {ceo_requests.count()}")
        
        # Now filter by affiliate (this might be missing!)
        affiliate_requests = ceo_requests.filter(
            Q(employee__affiliate=ceo.affiliate) | Q(employee__department__affiliate=ceo.affiliate)
        )
        print(f"  Requests from CEO's affiliate: {affiliate_requests.count()}")
        
        # Show sample requests
        for req in affiliate_requests[:3]:
            print(f"    - Request {req.id}: {req.employee.get_full_name()} ({req.status})")
            can_approve = ApprovalWorkflowService.can_user_approve(req, ceo)
            print(f"      Can approve: {can_approve}")

def main():
    """Run all tests."""
    test_ceo_approval_visibility()
    test_leave_request_filtering()

if __name__ == "__main__":
    main()