import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.models import LeaveRequest

print("Detailed check of LR#53, #52, #54, #50")
print("=" * 70)

for lr_id in [53, 52, 54, 50, 57]:
    try:
        lr = LeaveRequest.objects.get(id=lr_id)
        print(f"\nLR#{lr.id} - {lr.employee.get_full_name()}")
        print(f"  Status: {lr.status}")
        
        # Check employee
        emp = lr.employee
        print(f"  Employee: {emp.email}")
        
        # Check department
        if hasattr(emp, 'department') and emp.department:
            print(f"  Department: {emp.department.name}")
            if hasattr(emp.department, 'affiliate') and emp.department.affiliate:
                print(f"  Dept->Affiliate: {emp.department.affiliate.name}")
            else:
                print(f"  Dept->Affiliate: None")
        else:
            print(f"  Department: None")
        
        # Check user affiliate
        if hasattr(emp, 'affiliate') and emp.affiliate:
            print(f"  User->Affiliate: {emp.affiliate.name}")
        else:
            print(f"  User->Affiliate: None")
        
        print(f"  Dynamic Status: {lr.get_dynamic_status_display()}")
    except LeaveRequest.DoesNotExist:
        print(f"\nLR#{lr_id} does not exist")
