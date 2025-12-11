#!/usr/bin/env python3
"""Debug HR user setup and department assignment issues"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Department, Affiliate
from leaves.models import LeaveRequest

User = get_user_model()

print('=== HR USER ANALYSIS ===')
hr_user = User.objects.get(username='hradmin')
print(f'HR User: {hr_user.username} | {hr_user.get_full_name()}')
print(f'  Role: {hr_user.role}')
print(f'  Affiliate: {hr_user.affiliate.name if hr_user.affiliate else "None"}')
print(f'  Department: {hr_user.department.name if hr_user.department else "None"}')
if hr_user.department:
    print(f'  Department Affiliate: {hr_user.department.affiliate.name if hr_user.department.affiliate else "None"}')

print('\n=== DEPARTMENT ANALYSIS ===')
deps = Department.objects.all().order_by('affiliate__name', 'name')
for dept in deps:
    aff_name = dept.affiliate.name if dept.affiliate else 'None'
    hod_name = dept.hod.username if dept.hod else 'None'
    print(f'Dept: {dept.name} | Affiliate: {aff_name} | HOD: {hod_name}')

print('\n=== SDSL/SBL CEO DEPARTMENT ISSUE ===')
# Check why SDSL/SBL CEOs have Executive department
sdsl_ceo = User.objects.get(username='sdslceo')
sbl_ceo = User.objects.get(username='sblceo')

print(f'SDSL CEO: {sdsl_ceo.username}')
print(f'  Affiliate: {sdsl_ceo.affiliate.name if sdsl_ceo.affiliate else "None"}')
print(f'  Department: {sdsl_ceo.department.name if sdsl_ceo.department else "None"}')
if sdsl_ceo.department:
    print(f'  Dept Affiliate: {sdsl_ceo.department.affiliate.name if sdsl_ceo.department.affiliate else "None"}')

print(f'SBL CEO: {sbl_ceo.username}')
print(f'  Affiliate: {sbl_ceo.affiliate.name if sbl_ceo.affiliate else "None"}')
print(f'  Department: {sbl_ceo.department.name if sbl_ceo.department else "None"}')
if sbl_ceo.department:
    print(f'  Dept Affiliate: {sbl_ceo.department.affiliate.name if sbl_ceo.department.affiliate else "None"}')

print('\n=== AFFILIATE VISIBILITY TEST ===')
# Check if the users appear in affiliate-filtered queries
merban_aff = Affiliate.objects.get(name='Merban Capital')
sdsl_aff = Affiliate.objects.get(name='SDSL')
sbl_aff = Affiliate.objects.get(name='SBL')

print('Merban users:')
merban_users = User.objects.filter(affiliate=merban_aff)
for u in merban_users:
    print(f'  {u.username} | {u.role}')

print('SDSL users:')
sdsl_users = User.objects.filter(affiliate=sdsl_aff)
for u in sdsl_users:
    print(f'  {u.username} | {u.role}')

print('SBL users:')
sbl_users = User.objects.filter(affiliate=sbl_aff)
for u in sbl_users:
    print(f'  {u.username} | {u.role}')

print('\n=== RECENT REQUEST WORKFLOW ANALYSIS ===')
recent_requests = LeaveRequest.objects.order_by('-id')[:3]
for lr in recent_requests:
    print(f'\nLR#{lr.id} - {lr.employee.username} ({lr.employee.affiliate.name if lr.employee.affiliate else "No aff"})')
    print(f'  Status: {lr.status}')
    print(f'  Manager approved by: {lr.manager_approved_by.username if lr.manager_approved_by else "None"}')
    print(f'  HR approved by: {lr.hr_approved_by.username if lr.hr_approved_by else "None"}') 
    print(f'  CEO approved by: {lr.ceo_approved_by.username if lr.ceo_approved_by else "None"}')