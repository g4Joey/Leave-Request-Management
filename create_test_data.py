#!/usr/bin/env python3
"""
Create test leave requests to verify queue filtering fixes
"""

import os
import django
import sys

# Setup Django
sys.path.append('/d/Desktop/Leave management')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from leaves.models import LeaveRequest, LeaveType
from users.models import CustomUser
from datetime import date, timedelta
from leaves.services import ApprovalWorkflowService

def create_test_requests():
    """Create test leave requests to verify our filtering fixes"""
    print("=== Creating Test Leave Requests ===\n")
    
    # Get users
    manager = CustomUser.objects.filter(role='manager').first()  # jmankoe
    hr_user = CustomUser.objects.filter(role='hr').first()       # hradmin  
    ceo_user = CustomUser.objects.filter(role='ceo').first()     # ceo
    
    print(f"Test users:")
    print(f"  Manager: {manager.email if manager else 'None'}")
    print(f"  HR: {hr_user.email if hr_user else 'None'}")  
    print(f"  CEO: {ceo_user.email if ceo_user else 'None'}")
    
    # Get leave type
    leave_type = LeaveType.objects.filter(is_active=True).first()
    if not leave_type:
        leave_type = LeaveType.objects.create(
            name="Annual Leave",
            description="Annual vacation leave",
            is_active=True
        )
        print(f"Created leave type: {leave_type.name}")
    else:
        print(f"Using leave type: {leave_type.name}")
    
    # Clean up any existing test requests first
    test_requests = LeaveRequest.objects.filter(
        employee__email__in=[
            'jmankoe@umbcapital.com', 
            'hradmin@umbcapital.com'
        ]
    )
    if test_requests.exists():
        print(f"Cleaning up {test_requests.count()} existing test requests")
        test_requests.delete()
    
    requests_created = []
    
    # 1. Create manager request (should NOT appear in manager queue)
    if manager:
        try:
            mgr_request = LeaveRequest.objects.create(
                employee=manager,
                leave_type=leave_type,
                start_date=date.today() + timedelta(days=10),
                end_date=date.today() + timedelta(days=12),
                total_days=3,
                reason="Manager test request"
            )
            print(f"✅ Created manager request: {mgr_request.id}")
            requests_created.append(mgr_request)
        except Exception as e:
            print(f"❌ Failed to create manager request: {e}")
    
    # 2. Create HR request (should NOT appear in manager queue)  
    if hr_user:
        try:
            hr_request = LeaveRequest.objects.create(
                employee=hr_user,
                leave_type=leave_type,
                start_date=date.today() + timedelta(days=15),
                end_date=date.today() + timedelta(days=17),
                total_days=3,
                reason="HR test request"
            )
            print(f"✅ Created HR request: {hr_request.id}")
            requests_created.append(hr_request)
        except Exception as e:
            print(f"❌ Failed to create HR request: {e}")
    
    # 3. Move one request to manager_approved status (for HR queue testing)
    if requests_created:
        try:
            test_req = requests_created[0]
            test_req.status = 'manager_approved'
            test_req.manager_approved_by = ceo_user  # Use CEO as mock manager
            test_req.save()
            print(f"✅ Set request {test_req.id} to manager_approved status")
        except Exception as e:
            print(f"❌ Failed to update status: {e}")
    
    print(f"\nCreated {len(requests_created)} test requests")
    
    # Now test the filtering
    print(f"\n=== Testing Queue Filters with Test Data ===")
    
    from django.db.models import Q
    
    # Test manager queue (should be empty - no staff requests)
    manager_queue = LeaveRequest.objects.filter(status='pending').exclude(
        employee__role__in=['manager', 'hr', 'ceo', 'admin']
    )
    print(f"Manager queue (staff-only): {manager_queue.count()} items")
    
    # Test old broken filter (would include manager/CEO requests)
    old_broken = LeaveRequest.objects.filter(status='pending').exclude(
        employee__role__in=['hr', 'admin'] 
    )
    print(f"Old broken filter: {old_broken.count()} items")
    if old_broken.exists():
        print("  Items in old broken filter:")
        for req in old_broken:
            print(f"    - {req.employee.email} ({req.employee.role}) - THIS WOULD BE WRONG!")
    
    # Test HR queue
    merban_mgr_approved = LeaveRequest.objects.filter(status='manager_approved').filter(
        Q(employee__department__affiliate__name__iexact='MERBAN CAPITAL') |
        Q(employee__affiliate__name__iexact='MERBAN CAPITAL')
    ).exclude(employee__role='admin')
    
    ceo_approved = LeaveRequest.objects.filter(status='ceo_approved').exclude(employee__role='admin')
    
    print(f"HR queue:")
    print(f"  Merban manager_approved: {merban_mgr_approved.count()}")
    print(f"  CEO approved (all): {ceo_approved.count()}")
    print(f"  Total HR queue: {merban_mgr_approved.count() + ceo_approved.count()}")
    
    if merban_mgr_approved.exists():
        print("  Merban manager_approved items:")
        for req in merban_mgr_approved:
            print(f"    - {req.employee.email} ({req.employee.role})")

if __name__ == '__main__':
    create_test_requests()