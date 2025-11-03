import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.models import LeaveRequest
from users.models import CustomUser
from django.db.models import Q

print("=" * 80)
print("HR APPROVALS DEBUG")
print("=" * 80)

# Check for requests in different statuses
print("\n1. MANAGER_APPROVED requests (should show in HR queue for Merban):")
manager_approved = LeaveRequest.objects.filter(status='manager_approved')
print(f"   Total: {manager_approved.count()}")
for lr in manager_approved:
    emp_affiliate = lr.employee.department.affiliate.name if lr.employee.department and lr.employee.department.affiliate else (lr.employee.affiliate.name if lr.employee.affiliate else 'None')
    emp_dept = lr.employee.department.name if lr.employee.department else 'None'
    print(f"   - ID {lr.id}: {lr.employee.username} ({emp_affiliate} / {emp_dept}), Status: {lr.status}")

print("\n2. CEO_APPROVED requests (should show in HR queue for SDSL/SBL):")
ceo_approved = LeaveRequest.objects.filter(status='ceo_approved')
print(f"   Total: {ceo_approved.count()}")
for lr in ceo_approved:
    emp_affiliate = lr.employee.department.affiliate.name if lr.employee.department and lr.employee.department.affiliate else (lr.employee.affiliate.name if lr.employee.affiliate else 'None')
    emp_dept = lr.employee.department.name if lr.employee.department else 'None'
    print(f"   - ID {lr.id}: {lr.employee.username} ({emp_affiliate} / {emp_dept}), Status: {lr.status}")

print("\n3. HR_APPROVED requests (final approval from HR):")
hr_approved = LeaveRequest.objects.filter(status='hr_approved')
print(f"   Total: {hr_approved.count()}")
for lr in hr_approved:
    emp_affiliate = lr.employee.department.affiliate.name if lr.employee.department and lr.employee.department.affiliate else (lr.employee.affiliate.name if lr.employee.affiliate else 'None')
    print(f"   - ID {lr.id}: {lr.employee.username} ({emp_affiliate}), Status: {lr.status}")

print("\n4. PENDING requests:")
pending = LeaveRequest.objects.filter(status='pending')
print(f"   Total: {pending.count()}")
for lr in pending[:5]:
    emp_affiliate = lr.employee.department.affiliate.name if lr.employee.department and lr.employee.department.affiliate else (lr.employee.affiliate.name if lr.employee.affiliate else 'None')
    print(f"   - ID {lr.id}: {lr.employee.username} ({emp_affiliate}), Status: {lr.status}")

# Check what the HR queue logic would return
print("\n5. SIMULATING HR QUEUE LOGIC:")
print("   Merban requests (manager_approved, excluding SDSL/SBL):")
merban_qs = LeaveRequest.objects.filter(status='manager_approved').exclude(
    Q(employee__department__affiliate__name__in=['SDSL', 'SBL']) | 
    Q(employee__affiliate__name__in=['SDSL', 'SBL'])
).exclude(employee__role='admin')
print(f"   Count: {merban_qs.count()}")
for lr in merban_qs:
    print(f"   - ID {lr.id}: {lr.employee.username}")

print("\n   SDSL/SBL requests (ceo_approved):")
sdsl_sbl_qs = LeaveRequest.objects.filter(status='ceo_approved').filter(
    Q(employee__department__affiliate__name__in=['SDSL', 'SBL']) | 
    Q(employee__affiliate__name__in=['SDSL', 'SBL'])
).exclude(employee__role='admin')
print(f"   Count: {sdsl_sbl_qs.count()}")
for lr in sdsl_sbl_qs:
    print(f"   - ID {lr.id}: {lr.employee.username}")

print("\n6. CHECKING ADMIN USERS:")
admin_users = CustomUser.objects.filter(role='admin')
print(f"   Total admin users: {admin_users.count()}")
for u in admin_users:
    print(f"   - {u.username} ({u.email})")
    admin_requests = LeaveRequest.objects.filter(employee=u)
    print(f"     Leave requests: {admin_requests.count()}")

print("\n" + "=" * 80)
print("DEBUG COMPLETE")
print("=" * 80)
