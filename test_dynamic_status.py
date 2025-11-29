import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.models import LeaveRequest

print("Testing Dynamic Status Display")
print("=" * 70)

# Test various leave requests
test_requests = LeaveRequest.objects.filter(
    status__in=['pending', 'manager_approved', 'hr_approved', 'ceo_approved', 'approved', 'rejected']
).select_related('employee', 'employee__department', 'employee__department__affiliate')[:10]

for lr in test_requests:
    affiliate = "Unknown"
    if hasattr(lr.employee, 'department') and lr.employee.department:
        if hasattr(lr.employee.department, 'affiliate') and lr.employee.department.affiliate:
            affiliate = lr.employee.department.affiliate.name
    
    print(f"\nLR#{lr.id} - {lr.employee.get_full_name()}")
    print(f"  Affiliate: {affiliate}")
    print(f"  Raw Status: {lr.status}")
    print(f"  Dynamic Display: {lr.get_dynamic_status_display()}")
    print(f"  Standard Display: {lr.get_status_display()}")

print("\n" + "=" * 70)
print("Testing specific workflows:")

# SDSL/SBL requests (CEO-first flow)
print("\n--- SDSL/SBL (CEO → HR) ---")
sdsl_sbl = LeaveRequest.objects.filter(
    employee__department__affiliate__name__in=['SDSL', 'SBL']
).select_related('employee', 'employee__department', 'employee__department__affiliate')[:5]

for lr in sdsl_sbl:
    print(f"LR#{lr.id} ({lr.employee.department.affiliate.name}): {lr.status} → '{lr.get_dynamic_status_display()}'")

# Merban requests (Manager → HR → CEO)
print("\n--- Merban Capital (Manager → HR → CEO) ---")
merban = LeaveRequest.objects.filter(
    employee__department__affiliate__name='Merban Capital'
).select_related('employee', 'employee__department', 'employee__department__affiliate')[:5]

for lr in merban:
    print(f"LR#{lr.id}: {lr.status} → '{lr.get_dynamic_status_display()}'")

print("\nTest complete!")
