"""
Clean up: Delete Eric Nartey and Executive department
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser, Department

print("=" * 80)
print("CLEANUP: DELETE ERIC NARTEY AND EXECUTIVE DEPARTMENT")
print("=" * 80)

# Delete Eric Nartey
print("\n1. Deleting Eric Nartey...")
eric = CustomUser.objects.filter(first_name__icontains='eric', last_name__icontains='nartey').first()
if eric:
    print(f"   Found: {eric.get_full_name()} ({eric.email})")
    print(f"   Role: {eric.role}")
    print(f"   Affiliate: {eric.affiliate.name if eric.affiliate else 'None'}")
    
    # Check for any leave requests
    leave_requests = eric.leave_requests.all()
    print(f"   Leave requests: {leave_requests.count()}")
    
    confirm = input(f"\n   Delete {eric.get_full_name()}? (yes/no): ")
    if confirm.lower() == 'yes':
        eric_email = eric.email
        eric.delete()
        print(f"   ✓ Deleted: {eric_email}")
    else:
        print(f"   Skipped deletion")
else:
    print("   Eric Nartey not found")

# Delete Executive department
print("\n2. Deleting Executive department...")
exec_depts = Department.objects.filter(name__iexact='executive')
if exec_depts.exists():
    for dept in exec_depts:
        users_in_dept = CustomUser.objects.filter(department=dept)
        print(f"   Found: {dept.name} (id={dept.pk}, affiliate={dept.affiliate.name if dept.affiliate else 'None'})")
        print(f"   Users in department: {users_in_dept.count()}")
        
        if users_in_dept.exists():
            print(f"   ⚠ WARNING: Department has users! Cannot delete safely.")
            for u in users_in_dept:
                print(f"      - {u.get_full_name()} ({u.role})")
        else:
            dept.delete()
            print(f"   ✓ Deleted: Executive department")
else:
    print("   No Executive departments found")

print("\n" + "=" * 80)
print("CLEANUP COMPLETE")
print("=" * 80)

# Verify
print("\nVerification:")
eric_check = CustomUser.objects.filter(first_name__icontains='eric', last_name__icontains='nartey').exists()
exec_check = Department.objects.filter(name__iexact='executive').exists()

print(f"  Eric Nartey exists: {eric_check} {'❌' if eric_check else '✓'}")
print(f"  Executive dept exists: {exec_check} {'❌' if exec_check else '✓'}")
