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
from leaves.models import LeaveRequest, LeaveType
from datetime import datetime, timedelta

User = get_user_model()

def create_test_request():
    print("=== Creating Fresh Test Request ===")
    
    # Get aakorfu (staff member) and jmankoe (manager)
    staff = User.objects.filter(username='aakorfu').first()
    manager = User.objects.filter(username='jmankoe').first()
    leave_type = LeaveType.objects.filter(name='Annual Leave').first()
    
    if not all([staff, manager, leave_type]):
        print("ERROR: Missing required users or leave type!")
        return
    
    # Create a future-dated request
    start_date = datetime.now().date() + timedelta(days=7)  # Next week
    end_date = start_date + timedelta(days=2)  # 3-day leave
    
    # Delete old test requests to avoid confusion
    old_requests = LeaveRequest.objects.filter(employee=staff, start_date__gte=datetime.now().date())
    if old_requests.exists():
        print(f"Deleting {old_requests.count()} old future test requests...")
        old_requests.delete()
    
    # Create new request
    new_request = LeaveRequest.objects.create(
        employee=staff,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason="Test request for manager approval flow",
        status='pending'
    )
    
    print(f"✓ Created new test request #{new_request.pk}")
    print(f"  Employee: {staff.username} (reports to: {staff.manager.username if staff.manager else 'None'})")
    print(f"  Leave Type: {leave_type.name}")
    print(f"  Dates: {start_date} to {end_date} ({new_request.total_days} working days)")
    print(f"  Status: {new_request.status}")
    
    print("\n=== Ready for Testing ===")
    print("1. Log in as jmankoe")
    print("2. Go to Manager tab")
    print("3. You should see the new request with green 'Approve' and red 'Reject' buttons")
    print("4. Click 'Approve' to test Manager → HR → CEO flow")
    
    return new_request

if __name__ == '__main__':
    create_test_request()