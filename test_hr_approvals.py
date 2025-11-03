import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.models import LeaveRequest
from users.models import CustomUser
from django.db.models import Q

print("=== Testing HR Approvals Query ===\n")

# Check for requests with manager_approved status
print("1. Checking manager_approved requests (Merban only):")
merban_qs = LeaveRequest.objects.filter(status='manager_approved').exclude(
    Q(employee__department__affiliate__name__in=['SDSL', 'SBL']) |
    Q(employee__affiliate__name__in=['SDSL', 'SBL'])
).exclude(employee__role='admin')
print(f"   Count: {merban_qs.count()}")
for req in merban_qs[:3]:
    emp_aff = req.employee.department.affiliate.name if req.employee.department and req.employee.department.affiliate else req.employee.affiliate.name if req.employee.affiliate else "None"
    print(f"   - ID {req.id}: {req.employee.get_full_name()} ({emp_aff}), Status: {req.status}")

print("\n2. Checking ceo_approved requests (SDSL/SBL):")
ceo_approved_qs = LeaveRequest.objects.filter(status='ceo_approved').exclude(employee__role='admin')
print(f"   Count: {ceo_approved_qs.count()}")
for req in ceo_approved_qs[:3]:
    emp_aff = req.employee.department.affiliate.name if req.employee.department and req.employee.department.affiliate else req.employee.affiliate.name if req.employee.affiliate else "None"
    print(f"   - ID {req.id}: {req.employee.get_full_name()} ({emp_aff}), Status: {req.status}")

print("\n3. Testing union():")
try:
    union_qs = merban_qs.union(ceo_approved_qs)
    print(f"   Union count: {union_qs.count()}")
    
    # Try to iterate
    for req in union_qs[:3]:
        print(f"   - ID {req.id}: Employee ID {req.employee_id}, Status: {req.status}")
        # Try to access related fields
        try:
            emp_name = req.employee.get_full_name()
            print(f"     Employee name: {emp_name}")
        except Exception as e:
            print(f"     ERROR accessing employee: {e}")
            
except Exception as e:
    print(f"   ERROR with union: {e}")

print("\n4. Alternative approach - using Q objects:")
combined_qs = LeaveRequest.objects.filter(
    Q(status='manager_approved', ~Q(employee__department__affiliate__name__in=['SDSL', 'SBL']), ~Q(employee__affiliate__name__in=['SDSL', 'SBL'])) |
    Q(status='ceo_approved')
).exclude(employee__role='admin')
print(f"   Combined Q count: {combined_qs.count()}")
for req in combined_qs[:3]:
    emp_aff = req.employee.department.affiliate.name if req.employee.department and req.employee.department.affiliate else req.employee.affiliate.name if req.employee.affiliate else "None"
    print(f"   - ID {req.id}: {req.employee.get_full_name()} ({emp_aff}), Status: {req.status}")

print("\n5. Checking all leave request statuses:")
from django.db.models import Count
status_counts = LeaveRequest.objects.values('status').annotate(count=Count('id')).order_by('-count')
for item in status_counts:
    print(f"   {item['status']}: {item['count']}")
