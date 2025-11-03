import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.models import LeaveRequest
from users.models import CustomUser

# Convert any HR-submitted pending requests to hr_approved so they route to CEO
hr_users = CustomUser.objects.filter(role='hr')
qs = LeaveRequest.objects.filter(employee__in=hr_users, status='pending')
print(f"Found {qs.count()} HR pending requests to fix")

for lr in qs:
    print(f" - Fixing LR#{lr.id} from {lr.employee.email} ({lr.employee.role}) -> hr_approved")
    lr.status = 'hr_approved'
    lr.save(update_fields=['status','updated_at'])

print("Done.")
