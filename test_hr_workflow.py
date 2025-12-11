import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService

print("=" * 80)
print("TESTING HR USER WORKFLOW")
print("=" * 80)

hr_user = CustomUser.objects.filter(email__icontains='daatano').first()
if hr_user:
    print(f"\nHR User: {hr_user.get_full_name()}")
    print(f"Email: {hr_user.email}")
    print(f"Role: {hr_user.role}")
    print(f"Affiliate: {hr_user.affiliate.name if hr_user.affiliate else 'None'}")
    print(f"Department: {hr_user.department.name if hr_user.department else 'None'}")
    
    # Create test request
    test_req = LeaveRequest(employee=hr_user, status='pending')
    handler = ApprovalWorkflowService.get_handler(test_req)
    flow = handler.get_approval_flow()
    
    print(f"\n✅ NEW REQUIREMENT:")
    print(f"   HR requests should go: pending → hr → ceo")
    print(f"   (HR can approve their own request at HR approval stage)")
    
    print(f"\n📊 ACTUAL FLOW:")
    for status, next_role in flow.items():
        print(f"   {status} → {next_role}")
    
    print(f"\n📋 DYNAMIC STATUS:")
    print(f"   '{test_req.get_dynamic_status_display()}'")
    
    # Check if flow matches requirement
    expected = {'pending': 'hr', 'hr_approved': 'ceo'}
    if flow == expected:
        print(f"\n✅ PASS: HR workflow is correct!")
        print(f"   HR requests now follow manager flow (pending → hr → ceo)")
        print(f"   HR can self-approve at HR approval stage")
    else:
        print(f"\n❌ FAIL: HR workflow doesn't match requirement")
        print(f"   Expected: {expected}")
        print(f"   Got: {flow}")
    
    # Check if there are any existing HR requests
    existing = LeaveRequest.objects.filter(employee=hr_user).order_by('-created_at')
    print(f"\n📝 EXISTING HR REQUESTS: {existing.count()}")
    for req in existing[:3]:
        print(f"   #{req.pk}: {req.status} → {req.get_dynamic_status_display()}")
