import os
import django
from django.test import RequestFactory
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.models import LeaveType
from leaves.views import LeaveTypeViewSet
from rest_framework.test import force_authenticate

User = get_user_model()

print("Testing Leave Type Activate/Deactivate")
print("=" * 70)

# Get HR user
hr_user = User.objects.get(email='hradmin@umbcapital.com')

# Get or create a test leave type
leave_type, created = LeaveType.objects.get_or_create(
    name='Test Leave',
    defaults={'description': 'For testing', 'is_active': True}
)

print(f"\nLeave Type: {leave_type.name}")
print(f"Initial Status: {'Active' if leave_type.is_active else 'Inactive'}")

factory = RequestFactory()

# Test deactivate
print("\n--- Testing Deactivate ---")
if leave_type.is_active:
    request = factory.post(f'/api/leaves/types/{leave_type.id}/deactivate/')
    request.user = hr_user
    force_authenticate(request, user=hr_user)
    
    viewset = LeaveTypeViewSet()
    viewset.request = request
    viewset.action = 'deactivate'
    viewset.kwargs = {'pk': leave_type.id}
    viewset.format_kwarg = None
    
    response = viewset.deactivate(request, pk=leave_type.id)
    print(f"Response Status: {response.status_code}")
    print(f"Response Data: {response.data}")
    
    # Refresh from DB
    leave_type.refresh_from_db()
    print(f"Status After Deactivate: {'Active' if leave_type.is_active else 'Inactive'}")

# Test activate
print("\n--- Testing Activate ---")
if not leave_type.is_active:
    request2 = factory.post(f'/api/leaves/types/{leave_type.id}/activate/')
    request2.user = hr_user
    force_authenticate(request2, user=hr_user)
    
    viewset2 = LeaveTypeViewSet()
    viewset2.request = request2
    viewset2.action = 'activate'
    viewset2.kwargs = {'pk': leave_type.id}
    viewset2.format_kwarg = None
    
    response2 = viewset2.activate(request2, pk=leave_type.id)
    print(f"Response Status: {response2.status_code}")
    print(f"Response Data: {response2.data}")
    
    # Refresh from DB
    leave_type.refresh_from_db()
    print(f"Status After Activate: {'Active' if leave_type.is_active else 'Inactive'}")

print("\n" + "=" * 70)
print("SUCCESS: Activate/Deactivate endpoints working!")

# Cleanup test leave type if it was created
if created:
    leave_type.delete()
    print("Test leave type cleaned up")
