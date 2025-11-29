#!/usr/bin/env python
"""
Check Augustine Akorfu's department assignment.
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser

try:
    user = CustomUser.objects.get(email='aakorfu@umbcapital.com')
    print(f"User: {user.get_full_name()} ({user.email})")
    print(f"Role: {user.role}")
    print(f"Affiliate: {getattr(user.affiliate, 'name', 'None') if user.affiliate else 'None'}")
    
    if user.department:
        print(f"Department: {user.department.name}")
        print(f"Department ID: {user.department.id}")
        dept_aff = getattr(user.department.affiliate, 'name', 'None') if user.department.affiliate else 'None'
        print(f"Department Affiliate: {dept_aff}")
    else:
        print("Department: None")
        
except CustomUser.DoesNotExist:
    print("User aakorfu@umbcapital.com not found")
