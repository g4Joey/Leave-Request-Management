#!/usr/bin/env python
import os
import django
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.models import LeaveBalance
import json

User = get_user_model()

# Get a test user
user = User.objects.filter(username='jmankoe').first()
if user:
    print("=== RAW DATABASE STRUCTURE ===")
    print(f"Found user: {user.username}")
    
    # Check all balances for this user
    all_balances = LeaveBalance.objects.filter(employee=user)
    print(f"Total balances for user: {all_balances.count()}")
    
    if all_balances.count() > 0:
        for balance in all_balances:
            print(f"Year: {balance.year}")
            
    # Try current year balances  
    from datetime import datetime
    current_year = datetime.now().year
    print(f"Looking for year: {current_year}")
    balances = LeaveBalance.objects.filter(employee=user, year=current_year)
    for balance in balances:
        print(f"ID: {balance.id}")
        print(f"User: {balance.employee.username}")  
        print(f"Leave Type: {balance.leave_type.name}")
        print(f"Year: {balance.year}")
        print(f"Entitled Days: {balance.entitled_days}")
        print(f"Used Days: {balance.used_days}")
        print(f"Pending Days: {balance.pending_days}")
        remaining = balance.entitled_days - balance.used_days - balance.pending_days
        print(f"Calculated Remaining: {remaining}")
        print("---")
        
    print("\n=== SIMULATED API SERIALIZER OUTPUT ===")
    # Simulate what the serializer should return
    api_data = []
    for balance in balances:
        remaining = balance.entitled_days - balance.used_days - balance.pending_days
        api_data.append({
            'id': balance.id,
            'leave_type': balance.leave_type.name,
            'leave_type_name': balance.leave_type.name,
            'entitled_days': balance.entitled_days,
            'used_days': balance.used_days,
            'pending_days': balance.pending_days,
            'remaining_days': remaining,
            'year': balance.year
        })
    
    print(json.dumps(api_data, indent=2))