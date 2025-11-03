"""Test CEO approval permissions and affiliate filtering"""
from django.contrib.auth import get_user_model
from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService, ApprovalRoutingService

User = get_user_model()

print("\n=== Testing CEO Approval Flow ===\n")

# Get all CEOs
merban_ceo = User.objects.filter(email='ceo@umbcapital.com').first()
sdsl_ceo = User.objects.filter(email='sdslceo@umbcapital.com').first()
sbl_ceo = User.objects.filter(email='sblceo@umbcapital.com').first()

print("CEOs found:")
print(f"  Merban CEO: {merban_ceo.get_full_name() if merban_ceo else 'NOT FOUND'} - Affiliate: {merban_ceo.affiliate if merban_ceo else 'N/A'}")
print(f"  SDSL CEO: {sdsl_ceo.get_full_name() if sdsl_ceo else 'NOT FOUND'} - Affiliate: {sdsl_ceo.affiliate if sdsl_ceo else 'N/A'}")
print(f"  SBL CEO: {sbl_ceo.get_full_name() if sbl_ceo else 'NOT FOUND'} - Affiliate: {sbl_ceo.affiliate if sbl_ceo else 'N/A'}")

# Test hr_approved requests
print("\n=== Testing hr_approved Requests ===")
hr_approved_requests = LeaveRequest.objects.filter(status='hr_approved')[:5]
print(f"Found {hr_approved_requests.count()} hr_approved requests")

for req in hr_approved_requests:
    print(f"\nRequest #{req.id} by {req.employee.get_full_name()}")
    print(f"  Employee affiliate: {req.employee.affiliate}")
    if req.employee.department:
        print(f"  Department: {req.employee.department.name} (Affiliate: {req.employee.department.affiliate})")
    
    expected_ceo = ApprovalRoutingService.get_ceo_for_employee(req.employee)
    print(f"  Expected CEO: {expected_ceo.email if expected_ceo else 'None'}")
    
    handler = ApprovalWorkflowService.get_handler(req)
    print(f"  Handler: {handler.__class__.__name__}")
    
    # Test if each CEO can approve
    if merban_ceo:
        can_approve = handler.can_approve(merban_ceo, req.status)
        print(f"  Can Merban CEO approve? {can_approve}")
        if can_approve:
            print(f"    ✅ Merban CEO CAN approve this request")
    
    if sdsl_ceo:
        can_approve = handler.can_approve(sdsl_ceo, req.status)
        print(f"  Can SDSL CEO approve? {can_approve}")
    
    if sbl_ceo:
        can_approve = handler.can_approve(sbl_ceo, req.status)
        print(f"  Can SBL CEO approve? {can_approve}")

# Test pending requests (for SDSL/SBL flow)
print("\n=== Testing pending Requests (SDSL/SBL Flow) ===")
pending_requests = LeaveRequest.objects.filter(status='pending')[:5]
print(f"Found {pending_requests.count()} pending requests")

for req in pending_requests:
    emp_affiliate = req.employee.affiliate or (req.employee.department.affiliate if req.employee.department else None)
    affiliate_name = emp_affiliate.name if emp_affiliate else 'None'
    
    if affiliate_name.upper() in ['SDSL', 'SBL']:
        print(f"\nRequest #{req.id} by {req.employee.get_full_name()} ({affiliate_name})")
        
        handler = ApprovalWorkflowService.get_handler(req)
        print(f"  Handler: {handler.__class__.__name__}")
        print(f"  Status: {req.status}")
        
        # For SDSL/SBL, CEO should approve at pending stage
        if sdsl_ceo and affiliate_name.upper() == 'SDSL':
            can_approve = handler.can_approve(sdsl_ceo, req.status)
            print(f"  Can SDSL CEO approve? {can_approve}")
        
        if sbl_ceo and affiliate_name.upper() == 'SBL':
            can_approve = handler.can_approve(sbl_ceo, req.status)
            print(f"  Can SBL CEO approve? {can_approve}")

print("\n=== Test Complete ===")
