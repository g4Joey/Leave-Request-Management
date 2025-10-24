"""
Quick check of Merban Capital departments - run before and after update
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import Department, Affiliate

try:
    merban = Affiliate.objects.get(name='Merban Capital')
    print(f"\n{'='*70}")
    print(f"MERBAN CAPITAL DEPARTMENTS")
    print(f"{'='*70}")
    print(f"Affiliate ID: {merban.id}")
    print(f"Affiliate Name: {merban.name}")
    print(f"{'='*70}\n")
    
    depts = Department.objects.filter(affiliate=merban).order_by('name')
    
    if depts.exists():
        print(f"Total Departments: {depts.count()}\n")
        for i, dept in enumerate(depts, 1):
            staff_count = dept.customuser_set.count()
            manager = dept.manager.get_full_name() if dept.manager else "No manager assigned"
            hod = dept.hod.get_full_name() if dept.hod else "No HOD assigned"
            
            print(f"{i}. {dept.name}")
            print(f"   ID: {dept.id}")
            print(f"   Staff: {staff_count}")
            print(f"   Manager: {manager}")
            print(f"   HOD: {hod}")
            
            # Show staff members if any
            if staff_count > 0:
                staff = dept.customuser_set.all()[:5]  # Show first 5
                print(f"   Staff members:")
                for s in staff:
                    print(f"     • {s.get_full_name()} ({s.email})")
                if staff_count > 5:
                    print(f"     ... and {staff_count - 5} more")
            print()
    else:
        print("⚠️  NO DEPARTMENTS FOUND FOR MERBAN CAPITAL!")
        print("\nThis might be why you don't see departments on the web app.")
        print("Check if:")
        print("1. Departments were created for a different affiliate")
        print("2. The affiliate name is spelled differently")
        print("\nAll affiliates in database:")
        for aff in Affiliate.objects.all():
            dept_count = Department.objects.filter(affiliate=aff).count()
            print(f"  • {aff.name} (ID: {aff.id}) - {dept_count} departments")
    
except Affiliate.DoesNotExist:
    print("\n⚠️  MERBAN CAPITAL AFFILIATE NOT FOUND!")
    print("\nAvailable affiliates:")
    for aff in Affiliate.objects.all():
        dept_count = Department.objects.filter(affiliate=aff).count()
        print(f"  • {aff.name} (ID: {aff.id}) - {dept_count} departments")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
