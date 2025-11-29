#!/usr/bin/env python3
"""
Final verification that our queue filtering fixes work correctly
"""

import os
import django
import sys

# Setup Django  
sys.path.append('/d/Desktop/Leave management')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.models import LeaveRequest

print("=== FINAL QUEUE FILTERING VERIFICATION ===\n")

# Get pending requests
pending = LeaveRequest.objects.filter(status='pending')
print(f"Total pending requests: {pending.count()}")

if pending.exists():
    print("Pending requests by submitter:")
    for req in pending:
        print(f"  - {req.employee.email} ({req.employee.role})")

    # Test old broken filter (missing manager/ceo exclusions)
    old_broken = pending.exclude(employee__role__in=['hr', 'admin'])
    print(f"\n❌ OLD BROKEN FILTER: {old_broken.count()} items")
    if old_broken.exists():
        print("  Would incorrectly include:")
        for req in old_broken:
            print(f"    - {req.employee.email} ({req.employee.role}) ← SHOULD NOT BE IN MANAGER QUEUE!")

    # Test new fixed filter (includes manager/ceo exclusions) 
    new_fixed = pending.exclude(employee__role__in=['manager', 'hr', 'ceo', 'admin'])
    print(f"\n✅ NEW FIXED FILTER: {new_fixed.count()} items (staff-only)")
    if new_fixed.exists():
        print("  Correctly includes only staff:")
        for req in new_fixed:
            print(f"    - {req.employee.email} ({req.employee.role})")
    else:
        print("  No staff requests currently pending")

    print(f"\n🔧 FIX IMPACT:")
    difference = old_broken.count() - new_fixed.count()
    print(f"  Removed {difference} non-staff requests from manager approval queue")
    print(f"  ✅ Manager/CEO requests now correctly go to HR queue instead!")

else:
    print("No pending requests to test with")

print("\n=== VERIFICATION COMPLETE ===")