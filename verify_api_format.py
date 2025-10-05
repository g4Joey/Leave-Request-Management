#!/usr/bin/env python
import os
import django
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from leaves.models import LeaveType, LeaveBalance

User = get_user_model()

def simulate_api_response(username):
    """Simulate what the current_year_full API should return"""
    user = User.objects.filter(username=username).first()
    if not user:
        print(f"User {username} not found")
        return
        
    current_year = timezone.now().year
    types = list(LeaveType.objects.filter(is_active=True))
    balances = LeaveBalance.objects.filter(employee=user, year=current_year)
    by_lt = {b.leave_type_id: b for b in balances}
    
    items = []
    for lt in types:
        b = by_lt.get(lt.id)
        entitled = b.entitled_days if b else 0
        used = b.used_days if b else 0
        pending = b.pending_days if b else 0
        remaining = max(0, entitled - used - pending)
        items.append({
            'leave_type': {
                'id': lt.id,
                'name': lt.name,
            },
            'entitled_days': entitled,
            'used_days': used,
            'pending_days': pending,
            'remaining_days': remaining,
            'year': current_year,
        })
    
    return items

# Test with the jmankoe user
print("=== SIMULATED API RESPONSE ===")
import json
response = simulate_api_response('jmankoe')
print(json.dumps(response, indent=2))
print(f"\nResponse is array: {type(response) == list}")
print(f"Response length: {len(response) if response else 0}")

# Test individual item structure
if response:
    print(f"\nFirst item structure:")
    print(f"- leave_type.name: {response[0]['leave_type']['name']}")
    print(f"- entitled_days: {response[0]['entitled_days']}")
    print(f"- remaining_days: {response[0]['remaining_days']}")