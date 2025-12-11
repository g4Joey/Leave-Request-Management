import os
import django
from django.test import RequestFactory
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.views import LeaveRequestViewSet
from rest_framework.test import force_authenticate

User = get_user_model()

print("Testing Leave History Filtering")
print("=" * 70)

# Test different users
test_users = [
    'jmankoe@umbcapital.com',  # Joseph - Staff
    'hradmin@umbcapital.com',  # HR Admin
    'aakorfu@umbcapital.com',  # Augustine - Staff
]

factory = RequestFactory()

for email in test_users:
    try:
        user = User.objects.get(email=email)
        print(f"\n{user.get_full_name()} ({user.role}):")
        
        # Create request
        request = factory.get('/api/leaves/requests/history/')
        request.user = user  # Add user directly
        force_authenticate(request, user=user)
        
        # Create viewset
        viewset = LeaveRequestViewSet()
        viewset.request = request
        viewset.action = 'history'
        viewset.format_kwarg = None
        
        # Get queryset
        queryset = viewset.get_queryset()
        print(f"  Total requests visible: {queryset.count()}")
        
        # Show breakdown
        own_requests = queryset.filter(employee=user).count()
        other_requests = queryset.exclude(employee=user).count()
        
        print(f"  Own requests: {own_requests}")
        print(f"  Other users' requests: {other_requests}")
        
        if other_requests > 0:
            print(f"  WARNING: This user can see other users' requests!")
            # Show which users
            other_users = queryset.exclude(employee=user).values_list('employee__email', flat=True).distinct()
            print(f"  Can see requests from: {list(other_users)[:5]}")
        
    except User.DoesNotExist:
        print(f"\n{email}: User not found")

print("\n" + "=" * 70)
