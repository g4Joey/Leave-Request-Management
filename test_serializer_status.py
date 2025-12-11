import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from leaves.models import LeaveRequest
from leaves.serializers import LeaveRequestSerializer

print("=" * 60)
print("CHECKING SERIALIZER STATUS DISPLAY")
print("=" * 60)

# Check jmankoe's request
jmankoe = CustomUser.objects.filter(email__icontains='jmankoe').first()
if jmankoe:
    print(f'\nManager: {jmankoe.get_full_name()} ({jmankoe.email})')
    print(f'Role: {jmankoe.role}')
    
    recent_request = LeaveRequest.objects.filter(employee=jmankoe).order_by('-created_at').first()
    if recent_request:
        print(f'\nRequest #{recent_request.pk}:')
        print(f'  Status (DB): {recent_request.status}')
        print(f'  Status (display): {recent_request.get_status_display()}')
        print(f'  Status (dynamic): {recent_request.get_dynamic_status_display()}')
        
        # Test serializer
        serializer = LeaveRequestSerializer(recent_request)
        print(f'\nSerialized data:')
        print(f'  status: {serializer.data["status"]}')
        print(f'  status_display: {serializer.data["status_display"]}')
