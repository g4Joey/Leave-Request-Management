#!/usr/bin/env python3
"""Debug routing analysis for SDSL/SBL issues"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Affiliate, Department
from leaves.models import LeaveRequest
from leaves.services import ApprovalRoutingService

User = get_user_model()

print('=== USER AFFILIATE ANALYSIS ===')
for user in User.objects.filter(is_active=True).order_by('affiliate__name', 'username'):
    aff_name = user.affiliate.name if user.affiliate else 'None'
    dept_name = user.department.name if user.department else 'None'
    dept_aff = user.department.affiliate.name if user.department and user.department.affiliate else 'None'
    print(f'{user.username} | role={user.role} | user.affiliate={aff_name} | dept={dept_name} | dept.affiliate={dept_aff}')

print('\n=== CEO ROUTING TEST ===')
test_users = ['asanunu', 'enartey', 'jmankoe']
for username in test_users:
    try:
        user = User.objects.get(username=username)
        ceo = ApprovalRoutingService.get_ceo_for_employee(user)
        aff_name = ApprovalRoutingService.get_employee_affiliate_name(user)
        print(f'{username} -> affiliate={aff_name} -> ceo={ceo.username if ceo else None} ({ceo.affiliate.name if ceo and ceo.affiliate else "no aff"})')
    except User.DoesNotExist:
        print(f'{username} -> NOT FOUND')

print('\n=== RECENT LEAVE REQUESTS ===')
recent = LeaveRequest.objects.select_related('employee__affiliate', 'employee__department__affiliate').order_by('-created_at')[:10]
for lr in recent:
    emp_aff = lr.employee.affiliate.name if lr.employee.affiliate else 'None'
    dept_aff = lr.employee.department.affiliate.name if lr.employee.department and lr.employee.department.affiliate else 'None'
    print(f'LR#{lr.id} | {lr.employee.username} | status={lr.status} | emp.aff={emp_aff} | dept.aff={dept_aff}')

print('\n=== CEO USERS BY AFFILIATE ===')
ceos = User.objects.filter(role='ceo', is_active=True).order_by('affiliate__name')
for ceo in ceos:
    aff_name = ceo.affiliate.name if ceo.affiliate else 'None'
    print(f'CEO: {ceo.username} | {ceo.get_full_name()} | affiliate={aff_name}')