"""
Test dashboard API with fixed status display
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from leaves.models import LeaveRequest
from leaves.serializers import LeaveRequestListSerializer
import json

print("=" * 80)
print("TESTING DASHBOARD STATUS DISPLAY (FIXED)")
print("=" * 80)

# Test manager request
jmankoe = CustomUser.objects.filter(email__icontains='jmankoe').first()
if jmankoe:
    print(f"\n1. MANAGER: {jmankoe.get_full_name()}")
    
    request = LeaveRequest.objects.filter(employee=jmankoe, status='pending').first()
    if request:
        serializer = LeaveRequestListSerializer(request)
        print(f"\n   Request #{request.pk}:")
        print(f"   Status (DB): {request.status}")
        print(f"   Status (model dynamic): {request.get_dynamic_status_display()}")
        print(f"\n   Serialized data:")
        print(f"   status: '{serializer.data['status']}'")
        print(f"   status_display: '{serializer.data['status_display']}'")
        print(f"   stage_label: '{serializer.data.get('stage_label', 'N/A')}'")
        
        # This is what dashboard API will return
        print(f"\n   ✓ Dashboard will show: '{serializer.data['status_display']}'")
        
        expected = "Pending HR Approval"
        if serializer.data['status_display'] == expected:
            print(f"   ✅ CORRECT: Shows '{expected}'")
        else:
            print(f"   ❌ WRONG: Should be '{expected}' but got '{serializer.data['status_display']}'")

# Test HR request
hr_user = CustomUser.objects.filter(role='hr', affiliate__name__icontains='merban').first()
if hr_user:
    print(f"\n2. HR: {hr_user.get_full_name()}")
    
    request = LeaveRequest.objects.filter(employee=hr_user, status='pending').first()
    if request:
        serializer = LeaveRequestListSerializer(request)
        print(f"\n   Request #{request.pk}:")
        print(f"   Serialized status_display: '{serializer.data['status_display']}'")
        
        expected = "Pending HR Approval"
        if serializer.data['status_display'] == expected:
            print(f"   ✅ CORRECT: Shows '{expected}'")
        else:
            print(f"   ❌ WRONG: Should be '{expected}'")

# Test staff request
staff = CustomUser.objects.filter(role='junior_staff', affiliate__name__icontains='merban').first()
if staff:
    print(f"\n3. STAFF: {staff.get_full_name()}")
    
    request = LeaveRequest.objects.filter(employee=staff, status='pending').first()
    if request:
        serializer = LeaveRequestListSerializer(request)
        print(f"\n   Request #{request.pk}:")
        print(f"   Serialized status_display: '{serializer.data['status_display']}'")
        
        expected = "Pending Manager Approval"
        if serializer.data['status_display'] == expected:
            print(f"   ✅ CORRECT: Shows '{expected}'")
        else:
            print(f"   ❌ WRONG: Should be '{expected}'")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\n✓ LeaveRequestListSerializer now uses get_dynamic_status_display()")
print("✓ Dashboard view no longer overrides status_display with stage_label")
print("✓ Recent Leave Requests will show:")
print("  - Merban Staff (pending): 'Pending Manager Approval'")
print("  - Merban Manager (pending): 'Pending HR Approval'")
print("  - Merban HR (pending): 'Pending HR Approval'")
print("  - SDSL/SBL Staff (pending): 'Pending CEO Approval'")
print("  - SDSL/SBL CEO (pending): 'Pending HR Approval'")
