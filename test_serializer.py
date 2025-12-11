#!/usr/bin/env python
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.models import LeaveRequest
from leaves.serializers import LeaveRequestListSerializer

# Test serialization
lr = LeaveRequest.objects.select_related('employee__department', 'employee__affiliate').get(id=49)
s = LeaveRequestListSerializer(lr)

print(f"Employee: {lr.employee.get_full_name()}")
print(f"Actual Department: {lr.employee.department.name if lr.employee.department else 'None'}")
print(f"Actual Role: {lr.employee.role}")
print(f"\nSerialized Data:")
print(f"  employee_department: {s.data.get('employee_department')}")
print(f"  employee_role: {s.data.get('employee_role')}")
print(f"  employee_department_affiliate: {s.data.get('employee_department_affiliate')}")
