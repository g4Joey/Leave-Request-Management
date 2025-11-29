import os
import django
import json
from django.test import RequestFactory
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.views import ManagerLeaveViewSet
from rest_framework.test import force_authenticate

User = get_user_model()

print("Testing HR Approval Records API Response")
print("=" * 70)

# Get HR user
hr_user = User.objects.get(email='hradmin@umbcapital.com')
print(f"Testing as: {hr_user.get_full_name()} (HR)")

# Create request
factory = RequestFactory()
request = factory.get('/api/leave-requests/approval_records/')
force_authenticate(request, user=hr_user)

# Create viewset and call action
viewset = ManagerLeaveViewSet()
viewset.request = request
viewset.format_kwarg = None

# Call approval_records action
response = viewset.approval_records(request)

if response.status_code == 200:
    data = response.data
    print(f"\nTotal records: {data.get('count', 0)}")
    
    # Display first 5 records
    records = data.get('results', [])[:5]
    print(f"\nShowing first {len(records)} records:")
    print("-" * 70)
    
    for record in records:
        print(f"\nLR#{record['id']} - {record['employee_name']}")
        print(f"  Status (raw): {record['status']}")
        print(f"  Status Display: {record.get('status_display', 'N/A')}")
        print(f"  Affiliate: {record.get('employee_department_affiliate', 'N/A')}")
        print(f"  Leave Type: {record['leave_type_name']}")
else:
    print(f"Request failed: {response.status_code}")
    print(response.data)
