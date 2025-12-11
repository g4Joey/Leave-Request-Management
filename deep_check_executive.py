import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser, Department

print("=" * 60)
print("DETAILED CEO DEPARTMENT CHECK")
print("=" * 60)

# Get all CEOs
ceos = CustomUser.objects.filter(role='ceo')
for ceo in ceos:
    print(f'\n{ceo.get_full_name()}')
    print(f'  Email: {ceo.email}')
    print(f'  Affiliate: {ceo.affiliate.name if ceo.affiliate else "None"}')
    print(f'  Department (direct): {ceo.department}')
    print(f'  Department ID: {ceo.department_id}')
    
    if ceo.department:
        print(f'  Department name: {ceo.department.name}')
        print(f'  Department affiliate: {ceo.department.affiliate.name if ceo.department.affiliate else "None"}')

# Check all departments for Executive
print("\n" + "=" * 60)
print("ALL DEPARTMENTS CHECK")
print("=" * 60)

all_depts = Department.objects.all()
print(f'\nTotal departments: {all_depts.count()}')
for dept in all_depts:
    print(f'  - {dept.name} (id={dept.pk}, affiliate={dept.affiliate.name if dept.affiliate else None})')
    users_count = CustomUser.objects.filter(department=dept).count()
    print(f'    Users: {users_count}')

# Direct SQL check
from django.db import connection
print("\n" + "=" * 60)
print("RAW DATABASE CHECK")
print("=" * 60)

with connection.cursor() as cursor:
    # Check departments table
    cursor.execute("SELECT id, name, affiliate_id FROM users_department WHERE LOWER(name) LIKE '%executive%'")
    exec_depts = cursor.fetchall()
    print(f'\nDepartments with "executive" in name: {len(exec_depts)}')
    for dept in exec_depts:
        print(f'  - ID: {dept[0]}, Name: {dept[1]}, Affiliate: {dept[2]}')
    
    # Check users with those departments
    if exec_depts:
        exec_ids = [d[0] for d in exec_depts]
        placeholders = ','.join(['%s'] * len(exec_ids))
        cursor.execute(f"SELECT id, email, first_name, last_name, role, department_id FROM users_customuser WHERE department_id IN ({placeholders})", exec_ids)
        users = cursor.fetchall()
        print(f'\nUsers in executive departments: {len(users)}')
        for u in users:
            print(f'  - {u[2]} {u[3]} ({u[1]}): role={u[4]}, dept_id={u[5]}')
