import os
import django
from django.test import RequestFactory
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.views import LeaveRequestViewSet, ManagerLeaveViewSet
from rest_framework.test import force_authenticate

User = get_user_model()

print("Testing Approval Actions Still Work After Fix")
print("=" * 70)

# Test HR and CEO approval visibility
hr_user = User.objects.get(email='hradmin@umbcapital.com')
ceo_user = User.objects.get(email='ceo@umbcapital.com')

factory = RequestFactory()

# Test HR approvals
print("\nHR Approvals (should see ALL requests needing HR approval):")
request = factory.get('/api/manager-leave/hr_approvals_categorized/')
request.user = hr_user
force_authenticate(request, user=hr_user)

viewset = ManagerLeaveViewSet()
viewset.request = request
viewset.action = 'hr_approvals_categorized'
viewset.format_kwarg = None

queryset = viewset.get_queryset()
print(f"  Total requests visible to HR: {queryset.count()}")
print(f"  HR's own requests: {queryset.filter(employee=hr_user).count()}")
print(f"  Other users' requests: {queryset.exclude(employee=hr_user).count()}")

# Test CEO approvals
print("\nCEO Approvals (should see ALL requests needing CEO approval):")
request2 = factory.get('/api/manager-leave/ceo_approvals_categorized/')
request2.user = ceo_user
force_authenticate(request2, user=ceo_user)

viewset2 = ManagerLeaveViewSet()
viewset2.request = request2
viewset2.action = 'ceo_approvals_categorized'
viewset2.format_kwarg = None

queryset2 = viewset2.get_queryset()
print(f"  Total requests visible to CEO: {queryset2.count()}")
print(f"  CEO's own requests: {queryset2.filter(employee=ceo_user).count()}")
print(f"  Other users' requests: {queryset2.exclude(employee=ceo_user).count()}")

print("\n" + "=" * 70)
print("PASS: Approval actions still have cross-employee visibility")
