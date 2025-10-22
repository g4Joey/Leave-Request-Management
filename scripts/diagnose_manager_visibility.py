#!/usr/bin/env python
import os
import sys
import django

# Ensure project root is on sys.path when running as a script
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
	sys.path.insert(0, ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Department
from leaves.models import LeaveRequest

User = get_user_model()

def print_user(u):
	dept = getattr(u, 'department', None)
	mgr = getattr(u, 'manager', None)
	print(f"- {u.username} | role={getattr(u,'role',None)} | dept={getattr(dept,'name',None)} | direct_manager={getattr(mgr,'username',None)}")

def main():
	print("=== Manager Visibility Diagnosis ===")
	# 1) List departments and HODs
	print("\nDepartments and HODs (Department.manager):")
	for d in Department.objects.all():
		print(f"* {d.name} | HOD={getattr(d.manager,'username',None)}")

	# 2) Pick managers / HODs
	managers = User.objects.filter(role='manager')
	print(f"\nManagers found: {managers.count()}")
	for m in managers:
		print(f"\nManager: {m.username} (dept={getattr(getattr(m,'department',None),'name',None)})")
		# Direct reports
		direct = User.objects.filter(manager=m)
		print(f"  Direct reports ({direct.count()}):")
		for u in direct:
			print_user(u)
		# Department members if HOD
		hod_members = User.objects.filter(department__manager=m)
		print(f"  Dept members (HOD) ({hod_members.count()}):")
		for u in hod_members:
			print_user(u)

		# Pending requests visible to this manager/HOD
		visible = LeaveRequest.objects.filter(status='pending').filter(
			employee__manager=m
		) | LeaveRequest.objects.filter(status='pending').filter(
			employee__department__manager=m
		)
		print(f"  Pending requests visible: {visible.count()}")
		for r in visible.select_related('employee','leave_type'):
			print(f"    #{r.id} {r.employee.username} {r.leave_type.name} {r.start_date}→{r.end_date} status={r.status}")

	# 3) Sanity: list a few pending requests and show their manager/HOD
	print("\nSample pending requests with routing:")
	for r in LeaveRequest.objects.filter(status='pending').select_related('employee__manager','employee__department__manager','leave_type')[:10]:
		emp = r.employee
		print(f"- req#{r.id} by {emp.username} | direct_manager={getattr(emp.manager,'username',None)} | dept={getattr(getattr(emp,'department',None),'name',None)} | hod={getattr(getattr(emp,'department',None),'manager',None)}")

if __name__ == '__main__':
	main()

