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
from leaves.models import LeaveRequest
from django.db.models import Q

User = get_user_model()

def test_manager_self_exclusion():
    print("=== Testing Manager Self-Exclusion Fix ===")
    
    # Get jmankoe (manager)
    manager = User.objects.filter(username='jmankoe').first()
    if not manager:
        print("ERROR: Manager jmankoe not found!")
        return
    
    print(f"Manager: {manager.username} (role: {manager.role})")
    
    # Test the old query (what we had before)
    old_query = LeaveRequest.objects.filter(
        Q(employee__manager=manager) | Q(employee__department__manager=manager)
    )
    print(f"Old query (includes self): {old_query.count()} requests")
    for req in old_query.select_related('employee'):
        if req.employee == manager:
            print(f"  ❌ FOUND SELF: Request #{req.pk} by {req.employee.username}")
        else:
            print(f"  ✓ Other: Request #{req.pk} by {req.employee.username}")
    
    # Test the new query (with exclusion)
    new_query = LeaveRequest.objects.filter(
        Q(employee__manager=manager) | Q(employee__department__manager=manager)
    ).exclude(employee=manager)
    print(f"\nNew query (excludes self): {new_query.count()} requests")
    for req in new_query.select_related('employee'):
        print(f"  ✓ Request #{req.pk} by {req.employee.username}")
    
    # Show manager's own requests (should not appear in manager view)
    own_requests = LeaveRequest.objects.filter(employee=manager)
    print(f"\nManager's own requests ({own_requests.count()}):")
    for req in own_requests:
        print(f"  - Request #{req.pk}: {req.leave_type.name} ({req.start_date} to {req.end_date}) - Status: {req.status}")

if __name__ == '__main__':
    test_manager_self_exclusion()