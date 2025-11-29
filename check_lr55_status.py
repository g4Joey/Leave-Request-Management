#!/usr/bin/env python
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.models import LeaveRequest

lr = LeaveRequest.objects.get(id=55)
print(f"LR#55 current status: {lr.status}")
print(f"CEO approved by: {lr.ceo_approved_by}")
print(f"CEO approval date: {lr.ceo_approval_date}")
print(f"Final approved_by: {lr.approved_by}")
print(f"Final approval_date: {lr.approval_date}")
