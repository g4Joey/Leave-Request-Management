#!/usr/bin/env python
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.models import LeaveRequest

# Find requests by status
print("Leave requests by status:")
for status in ['pending', 'manager_approved', 'hr_approved', 'ceo_approved', 'approved', 'rejected']:
    count = LeaveRequest.objects.filter(status=status).count()
    if count:
        print(f"  {status}: {count}")
        
# Show some hr_approved requests
print("\nHR-approved requests (awaiting CEO):")
for lr in LeaveRequest.objects.filter(status='hr_approved')[:5]:
    print(f"  LR#{lr.id} - {lr.employee.get_full_name()} ({lr.employee.affiliate.name}) - {lr.status}")

# Create a test request if none exist
if not LeaveRequest.objects.filter(status='hr_approved').exists():
    print("\n⚠ No HR-approved requests found. Creating test request...")
    from django.contrib.auth import get_user_model
    from leaves.models import LeaveType
    from datetime import datetime, timedelta
    
    User = get_user_model()
    manager = User.objects.filter(role='manager', affiliate__name='Merban Capital').first()
    leave_type = LeaveType.objects.first()
    
    if manager and leave_type:
        lr = LeaveRequest.objects.create(
            employee=manager,
            leave_type=leave_type,
            start_date=datetime.now().date(),
            end_date=(datetime.now() + timedelta(days=2)).date(),
            total_days=2,
            reason="Test request for CEO approval",
            status='hr_approved'  # Skip to HR approved for testing
        )
        print(f"✓ Created LR#{lr.id} in hr_approved status")
    else:
        print("❌ Could not create test request - missing manager or leave type")
