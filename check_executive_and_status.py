import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import Department, CustomUser
from leaves.models import LeaveRequest

print("=" * 60)
print("CHECKING EXECUTIVE DEPARTMENTS")
print("=" * 60)

execs = Department.objects.filter(name__icontains='executive')
print(f'\nExecutive departments found: {execs.count()}')
for d in execs:
    affiliate_name = d.affiliate.name if d.affiliate else 'None'
    print(f'  - "{d.name}" (id={d.pk}, affiliate={affiliate_name})')
    users_in_dept = CustomUser.objects.filter(department=d)
    print(f'    Users in this dept: {users_in_dept.count()}')
    for u in users_in_dept:
        print(f'      * {u.get_full_name()} - {u.role}')

print("\n" + "=" * 60)
print("CEO DEPARTMENT ASSIGNMENTS")
print("=" * 60)

ceos = CustomUser.objects.filter(role='ceo')
print(f'\nCEOs found: {ceos.count()}')
for u in ceos:
    affiliate_name = u.affiliate.name if u.affiliate else 'None'
    dept_name = u.department.name if u.department else 'None'
    print(f'  - {u.get_full_name()} ({affiliate_name}): department="{dept_name}"')

print("\n" + "=" * 60)
print("MANAGER LEAVE REQUEST STATUS DISPLAY")
print("=" * 60)

# Check jmankoe's latest request
jmankoe = CustomUser.objects.filter(email__icontains='jmankoe').first()
if jmankoe:
    print(f'\nManager: {jmankoe.get_full_name()} ({jmankoe.email})')
    print(f'Role: {jmankoe.role}')
    print(f'Department: {jmankoe.department.name if jmankoe.department else "None"}')
    print(f'Affiliate: {jmankoe.affiliate.name if jmankoe.affiliate else "None"}')
    
    recent_requests = LeaveRequest.objects.filter(employee=jmankoe).order_by('-created_at')[:3]
    print(f'\nRecent requests: {recent_requests.count()}')
    for req in recent_requests:
        print(f'\n  Request #{req.pk}:')
        print(f'    Status (DB): {req.status}')
        print(f'    Status (display): {req.get_status_display()}')
        print(f'    Status (dynamic): {req.get_dynamic_status_display()}')
        print(f'    Created: {req.created_at}')

# Check HR user
print("\n" + "=" * 60)
print("HR USER STATUS DISPLAY")
print("=" * 60)

hr_users = CustomUser.objects.filter(role='hr', affiliate__name='Merban Capital')
for hr_user in hr_users:
    print(f'\nHR: {hr_user.get_full_name()} ({hr_user.email})')
    print(f'Department: {hr_user.department.name if hr_user.department else "None"}')
    
    recent_requests = LeaveRequest.objects.filter(employee=hr_user).order_by('-created_at')[:2]
    print(f'Recent requests: {recent_requests.count()}')
    for req in recent_requests:
        print(f'\n  Request #{req.pk}:')
        print(f'    Status (DB): {req.status}')
        print(f'    Status (display): {req.get_status_display()}')
        print(f'    Status (dynamic): {req.get_dynamic_status_display()}')
