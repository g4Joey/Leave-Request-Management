#!/usr/bin/env python3
"""Debug manager approval queue filtering and CEO visibility"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService
from django.db.models import Q

User = get_user_model()

print('=== MANAGER QUEUE FILTERING TEST ===')
# Test manager queue logic for different users
hr_user = User.objects.get(username='hradmin')
admin_user = User.objects.get(username='admin')
jmankoe = User.objects.get(username='jmankoe')

print(f'HR user: {hr_user.username} | role={hr_user.role} | affiliate={hr_user.affiliate.name if hr_user.affiliate else None}')
print(f'Admin user: {admin_user.username} | role={admin_user.role}')
print(f'Jmankoe: {jmankoe.username} | role={jmankoe.role} | affiliate={jmankoe.affiliate.name if jmankoe.affiliate else None}')

print('\n=== CURRENT PENDING REQUESTS ANALYSIS ===')
all_pending = LeaveRequest.objects.filter(status='pending')
for lr in all_pending:
    emp_role = lr.employee.role
    emp_aff = lr.employee.affiliate.name if lr.employee.affiliate else 'None'
    dept_aff = lr.employee.department.affiliate.name if lr.employee.department and lr.employee.department.affiliate else 'None'
    
    # Test if this should be excluded from manager queue
    is_mgr_hr_ceo = emp_role in ['manager', 'hr', 'ceo']
    is_sdsl_sbl = (
        (lr.employee.department and lr.employee.department.affiliate and lr.employee.department.affiliate.name in ['SDSL', 'SBL']) or
        (lr.employee.affiliate and lr.employee.affiliate.name in ['SDSL', 'SBL'])
    )
    
    print(f'LR#{lr.id} | {lr.employee.username} | role={emp_role} | aff={emp_aff} | exclude_role={is_mgr_hr_ceo} | exclude_sdsl_sbl={is_sdsl_sbl}')

print('\n=== CEO CAN APPROVE ANALYSIS ===')
# Test CEO approval permissions for recent requests
recent_requests = LeaveRequest.objects.order_by('-id')[:5]
benjamin = User.objects.get(username='ceo')  # Merban CEO
kofi = User.objects.get(username='sdslceo')  # SDSL CEO
sbl_ceo = User.objects.get(username='sblceo')  # SBL CEO

for lr in recent_requests:
    print(f'\nLR#{lr.id} | {lr.employee.username} ({lr.employee.affiliate.name if lr.employee.affiliate else "No aff"}) | status={lr.status}')
    
    for ceo_user in [benjamin, kofi, sbl_ceo]:
        handler = ApprovalWorkflowService.get_handler(lr)
        can_approve = handler.can_approve(ceo_user, lr.status)
        print(f'  {ceo_user.username} ({ceo_user.affiliate.name if ceo_user.affiliate else "No aff"}) can approve: {can_approve}')

print('\n=== HR QUEUE FILTERING TEST ===')
print('Testing what HR should see:')

# Merban manager_approved (should see)
merban_mgr_approved = LeaveRequest.objects.filter(
    status='manager_approved',
    employee__affiliate__name__iexact='MERBAN CAPITAL'
).exclude(employee__role='admin')

print(f'Merban manager_approved (HR should see): {merban_mgr_approved.count()}')
for lr in merban_mgr_approved:
    print(f'  LR#{lr.id} | {lr.employee.username}')

# SDSL/SBL ceo_approved (should see)
ceo_approved = LeaveRequest.objects.filter(status='ceo_approved').exclude(employee__role='admin')
print(f'CEO approved (HR should see): {ceo_approved.count()}')
for lr in ceo_approved:
    print(f'  LR#{lr.id} | {lr.employee.username} | {lr.employee.affiliate.name if lr.employee.affiliate else "No aff"}')