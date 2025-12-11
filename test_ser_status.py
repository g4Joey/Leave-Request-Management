import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.models import LeaveRequest
from leaves.serializers import LeaveRequestListSerializer

print("Testing LeaveRequestListSerializer with Dynamic Status")
print("=" * 70)

# Get some leave requests
requests = LeaveRequest.objects.filter(
    status__in=['pending', 'manager_approved', 'hr_approved', 'ceo_approved', 'approved', 'rejected']
).select_related('employee', 'employee__department', 'employee__department__affiliate')[:10]

print(f"\nSerializing {requests.count()} requests:\n")

for lr in requests:
    serializer = LeaveRequestListSerializer(lr)
    data = serializer.data
    
    affiliate = data.get('employee_department_affiliate', 'Unknown')
    print(f"LR#{data['id']} - {data['employee_name']} ({affiliate})")
    print(f"  Status: {data['status']}")
    print(f"  Status Display: {data.get('status_display', 'N/A')}")
    print()
