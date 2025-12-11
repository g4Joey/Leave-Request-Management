"""
Test if the API returns correct status_display for manager requests
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from leaves.models import LeaveRequest
from leaves.serializers import LeaveRequestSerializer
import json

print("=" * 80)
print("TESTING STATUS DISPLAY FOR MANAGER/HR REQUESTS")
print("=" * 80)

# Test with jmankoe (manager)
jmankoe = CustomUser.objects.filter(email__icontains='jmankoe').first()
if jmankoe:
    print(f"\n1. MANAGER: {jmankoe.get_full_name()}")
    print(f"   Role: {jmankoe.role}")
    
    request = LeaveRequest.objects.filter(employee=jmankoe, status='pending').first()
    if request:
        print(f"\n   Request #{request.pk}:")
        print(f"   Status (DB): {request.status}")
        print(f"   Status (display): {request.get_status_display()}")
        print(f"   Status (dynamic): {request.get_dynamic_status_display()}")
        
        # Check serialized data
        serializer = LeaveRequestSerializer(request)
        print(f"\n   Serialized JSON:")
        print(f"   status: '{serializer.data['status']}'")
        print(f"   status_display: '{serializer.data['status_display']}'")
        
        # Check what the API would return
        print(f"\n   Full serialized data (relevant fields):")
        relevant_fields = {
            'id': serializer.data['id'],
            'employee_name': serializer.data['employee_name'],
            'status': serializer.data['status'],
            'status_display': serializer.data['status_display'],
        }
        print(json.dumps(relevant_fields, indent=2))
    else:
        print("   No pending requests found")

# Test with HR user
hr_user = CustomUser.objects.filter(role='hr', affiliate__name__icontains='merban').first()
if hr_user:
    print(f"\n2. HR: {hr_user.get_full_name()}")
    print(f"   Role: {hr_user.role}")
    
    request = LeaveRequest.objects.filter(employee=hr_user, status='pending').first()
    if request:
        print(f"\n   Request #{request.pk}:")
        print(f"   Status (DB): {request.status}")
        print(f"   Status (dynamic): {request.get_dynamic_status_display()}")
        
        serializer = LeaveRequestSerializer(request)
        print(f"\n   Serialized status_display: '{serializer.data['status_display']}'")
    else:
        print("   No pending requests found")

# Test with staff
staff = CustomUser.objects.filter(role='junior_staff', affiliate__name__icontains='merban').first()
if staff:
    print(f"\n3. STAFF: {staff.get_full_name()}")
    print(f"   Role: {staff.role}")
    
    request = LeaveRequest.objects.filter(employee=staff, status='pending').first()
    if request:
        print(f"\n   Request #{request.pk}:")
        print(f"   Status (DB): {request.status}")
        print(f"   Status (dynamic): {request.get_dynamic_status_display()}")
        
        serializer = LeaveRequestSerializer(request)
        print(f"\n   Serialized status_display: '{serializer.data['status_display']}'")
    else:
        print("   No pending requests found - creating test")
        from datetime import date, timedelta
        from leaves.models import LeaveType
        
        leave_type = LeaveType.objects.filter(is_active=True).first()
        if leave_type:
            test_request = LeaveRequest.objects.create(
                employee=staff,
                leave_type=leave_type,
                start_date=date.today() + timedelta(days=7),
                end_date=date.today() + timedelta(days=9),
                reason="Test request for staff",
                status='pending'
            )
            serializer = LeaveRequestSerializer(test_request)
            print(f"\n   Test Request #{test_request.pk}:")
            print(f"   Status (DB): {test_request.status}")
            print(f"   Status (dynamic): {test_request.get_dynamic_status_display()}")
            print(f"   Serialized status_display: '{serializer.data['status_display']}'")
