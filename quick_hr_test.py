import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService

# Find HR user
hr_user = CustomUser.objects.filter(role='hr', affiliate__name__icontains='merban').first()
print(f"Found HR: {hr_user}")

if hr_user:
    print(f"Name: {hr_user.get_full_name()}")
    print(f"Email: {hr_user.email}")
    print(f"Role: {hr_user.role}")
    
    # Test flow
    test_req = LeaveRequest(employee=hr_user, status='pending')
    handler = ApprovalWorkflowService.get_handler(test_req)
    flow = handler.get_approval_flow()
    
    print(f"Flow: {flow}")
    print(f"Display: {test_req.get_dynamic_status_display()}")
    
    if flow == {'pending': 'hr', 'hr_approved': 'ceo'}:
        print("SUCCESS: HR follows manager flow")
    else:
        print("FAIL: HR flow incorrect")
