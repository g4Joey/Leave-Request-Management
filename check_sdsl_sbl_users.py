import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.models import LeaveRequest
from users.models import CustomUser

print("Checking SDSL/SBL employees and their affiliates")
print("=" * 70)

# Check Abdul Sanunu and Esther Nartey
users = CustomUser.objects.filter(email__in=['abdulsanunu@umbcapital.com', 'esthernartey@umbcapital.com'])

for user in users:
    print(f"\n{user.get_full_name()} ({user.email})")
    print(f"  User Affiliate: {user.affiliate.name if user.affiliate else 'None'}")
    print(f"  Department: {user.department.name if user.department else 'None'}")
    if user.department and user.department.affiliate:
        print(f"  Dept Affiliate: {user.department.affiliate.name}")
    else:
        print(f"  Dept Affiliate: None")
    
    # Check their requests
    requests = LeaveRequest.objects.filter(employee=user).order_by('-id')[:3]
    print(f"  Recent requests:")
    for lr in requests:
        print(f"    LR#{lr.id}: {lr.status} → '{lr.get_dynamic_status_display()}'")
