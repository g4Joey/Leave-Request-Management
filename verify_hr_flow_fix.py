import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService

print("=" * 60)
print("VERIFYING HR FLOW CHANGE")
print("=" * 60)

# Check HR users in Merban
hr_users = CustomUser.objects.filter(role='hr', affiliate__name='Merban Capital')
print(f'\nMerban HR users: {hr_users.count()}')

for hr_user in hr_users:
    print(f'\n{hr_user.get_full_name()} ({hr_user.email})')
    print(f'  Department: {hr_user.department.name if hr_user.department else "None"}')
    
    # Create a test request to check the flow
    test_request = LeaveRequest(employee=hr_user, status='pending')
    handler = ApprovalWorkflowService.get_handler(test_request)
    flow = handler.get_approval_flow()
    
    print(f'\n  Approval flow:')
    for status, next_role in flow.items():
        print(f'    {status} -> {next_role}')
    
    # Check dynamic status
    print(f'\n  Dynamic status display for pending: {test_request.get_dynamic_status_display()}')
    
    # Check existing requests
    existing = LeaveRequest.objects.filter(employee=hr_user).order_by('-created_at')
    print(f'\n  Existing requests: {existing.count()}')
    for req in existing[:3]:
        print(f'    #{req.pk}: {req.status} -> {req.get_dynamic_status_display()}')

print("\n" + "=" * 60)
print("CHECKING MANAGER FLOW")
print("=" * 60)

jmankoe = CustomUser.objects.filter(email__icontains='jmankoe').first()
if jmankoe:
    print(f'\n{jmankoe.get_full_name()} ({jmankoe.email})')
    print(f'  Role: {jmankoe.role}')
    
    test_request = LeaveRequest(employee=jmankoe, status='pending')
    handler = ApprovalWorkflowService.get_handler(test_request)
    flow = handler.get_approval_flow()
    
    print(f'\n  Approval flow:')
    for status, next_role in flow.items():
        print(f'    {status} -> {next_role}')
    
    print(f'\n  Dynamic status display for pending: {test_request.get_dynamic_status_display()}')
    
    actual_request = LeaveRequest.objects.filter(employee=jmankoe).order_by('-created_at').first()
    if actual_request:
        print(f'\n  Latest request #{actual_request.pk}:')
        print(f'    Status: {actual_request.status}')
        print(f'    Display: {actual_request.get_dynamic_status_display()}')
