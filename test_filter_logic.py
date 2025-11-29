#!/usr/bin/env python3
"""
Simple test to verify queue filtering logic by checking the queryset construction
"""

import os
import django
import sys

# Setup Django
sys.path.append('/d/Desktop/Leave management')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from leaves.models import LeaveRequest
from users.models import CustomUser
from django.db.models import Q

def test_filtering_logic():
    """Test the filtering logic directly"""
    print("=== Testing Queue Filter Logic ===\n")
    
    # Get user counts by role
    manager_count = CustomUser.objects.filter(role='manager').count()
    hr_count = CustomUser.objects.filter(role='hr').count()  
    ceo_count = CustomUser.objects.filter(role='ceo').count()
    admin_count = CustomUser.objects.filter(role='admin').count()
    staff_count = CustomUser.objects.filter(role='staff').count()
    
    print(f"User counts by role:")
    print(f"  Managers: {manager_count}")
    print(f"  HR: {hr_count}")
    print(f"  CEOs: {ceo_count}")
    print(f"  Admins: {admin_count}")
    print(f"  Staff: {staff_count}")
    
    # Check pending leave requests by submitter role
    pending_requests = LeaveRequest.objects.filter(status='pending')
    print(f"\nPending requests: {pending_requests.count()}")
    
    for role in ['manager', 'hr', 'ceo', 'admin', 'staff']:
        role_requests = pending_requests.filter(employee__role=role)
        print(f"  From {role}s: {role_requests.count()}")
        if role_requests.exists():
            for req in role_requests[:3]:  # Show first 3
                print(f"    - {req.employee.email} ({req.leave_type.name})")
    
    # Test our NEW filter (staff-only for manager queue)
    print(f"\nTesting NEW manager queue filter (staff-only):")
    staff_only_filter = pending_requests.exclude(employee__role__in=['manager', 'hr', 'ceo', 'admin'])
    print(f"  Staff-only pending: {staff_only_filter.count()}")
    
    # Test old broken filter 
    print(f"\nTesting OLD manager queue filter (broken):")
    old_broken_filter = pending_requests.exclude(employee__role__in=['hr', 'admin'])
    print(f"  Old filter result: {old_broken_filter.count()}")
    print(f"  Difference: {old_broken_filter.count() - staff_only_filter.count()} (should be non-staff count)")
    
    # Show what the old filter was letting through incorrectly
    incorrectly_included = old_broken_filter.filter(employee__role__in=['manager', 'ceo'])
    if incorrectly_included.exists():
        print(f"  ❌ OLD FILTER BUG: Included {incorrectly_included.count()} manager/CEO requests:")
        for req in incorrectly_included:
            print(f"    - {req.employee.email} ({req.employee.role})")
    
    # Test HR queue logic
    print(f"\nTesting HR queue logic:")
    
    # Merban manager_approved items
    merban_manager_approved = LeaveRequest.objects.filter(
        status='manager_approved'
    ).filter(
        Q(employee__department__affiliate__name__iexact='MERBAN CAPITAL') |
        Q(employee__affiliate__name__iexact='MERBAN CAPITAL')
    ).exclude(employee__role='admin')
    print(f"  Merban manager_approved items: {merban_manager_approved.count()}")
    
    # All ceo_approved items (cross-affiliate for HR)
    ceo_approved = LeaveRequest.objects.filter(status='ceo_approved').exclude(employee__role='admin')
    print(f"  CEO-approved items (all affiliates): {ceo_approved.count()}")
    
    total_hr_queue = merban_manager_approved.count() + ceo_approved.count()
    print(f"  Total HR queue size: {total_hr_queue}")
    
    if ceo_approved.exists():
        print("  CEO-approved items by affiliate:")
        for req in ceo_approved:
            aff_name = req.employee.affiliate.name if req.employee.affiliate else req.employee.department.affiliate.name if req.employee.department and req.employee.department.affiliate else "Unknown"
            print(f"    - {req.employee.email} from {aff_name}")

if __name__ == '__main__':
    test_filtering_logic()