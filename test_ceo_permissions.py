#!/usr/bin/env python
"""
Test CEO approval permission for specific leave requests.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService, ApprovalRoutingService

def test_ceo_approval(lr_id, ceo_email):
    """Test if a CEO can approve a specific leave request."""
    print(f"\n{'='*80}")
    print(f"Testing CEO Approval for LR#{lr_id}")
    print(f"{'='*80}")
    
    try:
        lr = LeaveRequest.objects.get(id=lr_id)
        ceo = CustomUser.objects.get(email=ceo_email)
        
        print(f"Leave Request: #{lr.id}")
        print(f"  Employee: {lr.employee.get_full_name()} ({lr.employee.email})")
        print(f"  Employee Role: {lr.employee.role}")
        print(f"  Status: {lr.status}")
        
        # Get employee affiliate info
        emp_aff = getattr(lr.employee.affiliate, 'name', 'None') if lr.employee.affiliate else 'None'
        print(f"  Employee Affiliate (direct): {emp_aff}")
        
        if lr.employee.department:
            dept_aff = getattr(lr.employee.department.affiliate, 'name', 'None') if lr.employee.department.affiliate else 'None'
            print(f"  Employee Department: {lr.employee.department.name}")
            print(f"  Department Affiliate: {dept_aff}")
        
        routing_aff = ApprovalRoutingService.get_employee_affiliate_name(lr.employee)
        print(f"  Routing Service Affiliate: {routing_aff}")
        
        print(f"\nCEO: {ceo.get_full_name()} ({ceo.email})")
        print(f"  CEO Role: {ceo.role}")
        ceo_aff = getattr(ceo.affiliate, 'name', 'None') if ceo.affiliate else 'None'
        print(f"  CEO Affiliate: {ceo_aff}")
        print(f"  CEO ID: {ceo.id}")
        
        # Get expected CEO
        expected_ceo = ApprovalRoutingService.get_ceo_for_employee(lr.employee)
        print(f"\nExpected CEO:")
        if expected_ceo:
            print(f"  Email: {expected_ceo.email}")
            print(f"  ID: {expected_ceo.id}")
            print(f"  Match: {expected_ceo.id == ceo.id}")
        else:
            print(f"  NONE FOUND!")
        
        # Get handler
        handler = ApprovalWorkflowService.get_handler(lr)
        print(f"\nHandler: {handler.__class__.__name__}")
        
        # Get approval flow
        flow = handler.get_approval_flow()
        print(f"Approval Flow: {flow}")
        
        required_role = flow.get(lr.status)
        print(f"Required Role for status '{lr.status}': {required_role}")
        
        # Test can_approve
        can_approve = handler.can_approve(ceo, lr.status)
        print(f"\nCan Approve Result: {can_approve}")
        
        # Also test the service method
        can_approve_service = ApprovalWorkflowService.can_user_approve(lr, ceo)
        print(f"Service Can Approve Result: {can_approve_service}")
        
        if not can_approve:
            print("\n[DENIED] APPROVAL DENIED")
            print("Possible reasons:")
            print(f"  - CEO role mismatch? CEO role='{ceo.role}', Required='{required_role}'")
            print(f"  - CEO ID mismatch? CEO={ceo.id}, Expected={expected_ceo.id if expected_ceo else 'None'}")
            print(f"  - Affiliate mismatch? CEO affiliate='{ceo_aff}', Employee via routing='{routing_aff}'")
        else:
            print("\n[ALLOWED] APPROVAL ALLOWED")
            
    except LeaveRequest.DoesNotExist:
        print(f"[ERROR] Leave Request #{lr_id} not found")
    except CustomUser.DoesNotExist:
        print(f"[ERROR] CEO {ceo_email} not found")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    # Test cases based on the diagnostic output
    test_cases = [
        # Merban requests at hr_approved status
        (49, 'ceo@umbcapital.com'),  # Joseph Mankoe (manager)
        (48, 'ceo@umbcapital.com'),  # Augustine Akorfu
        (41, 'ceo@umbcapital.com'),  # HR user
        
        # SDSL requests at pending status
        (54, 'sdslceo@umbcapital.com'),
        (53, 'sdslceo@umbcapital.com'),
        
        # SBL request at pending status
        (52, 'sblceo@umbcapital.com'),
    ]
    
    for lr_id, ceo_email in test_cases:
        test_ceo_approval(lr_id, ceo_email)
    
    print(f"\n{'='*80}")
    print("TESTING COMPLETE")
    print(f"{'='*80}")

if __name__ == '__main__':
    main()
