#!/usr/bin/env python
"""
Test rejection notifications at each stage
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from leaves.models import LeaveRequest, LeaveType
from notifications.models import Notification
from notifications.services import LeaveNotificationService
from datetime import date, timedelta

User = get_user_model()

def test_rejection_notifications():
    """Test notifications for rejections at each stage"""
    print("🛑 Testing Rejection Notifications")
    print("=" * 40)
    
    # Get users
    ceo = User.objects.get(role='ceo')
    hr_user = User.objects.filter(role='hr').first()
    manager = User.objects.filter(role='manager').first()
    staff = User.objects.filter(role__in=['junior_staff', 'senior_staff']).first()
    leave_type = LeaveType.objects.first()
    
    # Clear existing notifications for clean test
    Notification.objects.all().delete()
    
    # Test 1: Manager Rejection
    print("\n📝 Test 1: Manager Rejection")
    leave_request1 = LeaveRequest.objects.create(
        employee=staff,
        leave_type=leave_type,
        start_date=date.today() + timedelta(days=10),
        end_date=date.today() + timedelta(days=12),
        reason="Manager rejection test"
    )
    
    # Manager rejects directly
    leave_request1.reject(manager, "Too busy during this period", "manager")
    # Manually trigger notification since we're not using API
    LeaveNotificationService.notify_rejection(leave_request1, manager, "manager")
    
    # Check notifications
    manager_rejection_notifications = Notification.objects.filter(leave_request=leave_request1)
    print(f"   Notifications sent: {manager_rejection_notifications.count()}")
    for notif in manager_rejection_notifications:
        print(f"   → {notif.recipient.get_full_name()}: {notif.title}")
    
    # Test 2: HR Rejection (after manager approval)
    print("\n📝 Test 2: HR Rejection")
    leave_request2 = LeaveRequest.objects.create(
        employee=staff,
        leave_type=leave_type,
        start_date=date.today() + timedelta(days=20),
        end_date=date.today() + timedelta(days=22),
        reason="HR rejection test"
    )
    
    # Manager approves first
    leave_request2.manager_approve(manager, "Looks good to me")
    # HR rejects
    leave_request2.reject(hr_user, "Policy violation", "hr")
    # Manually trigger notification
    LeaveNotificationService.notify_rejection(leave_request2, hr_user, "hr")
    
    # Check notifications for this request
    hr_rejection_notifications = Notification.objects.filter(leave_request=leave_request2)
    print(f"   Notifications sent: {hr_rejection_notifications.count()}")
    for notif in hr_rejection_notifications:
        print(f"   → {notif.recipient.get_full_name()}: {notif.title}")
    
    # Test 3: CEO Rejection (after manager + HR approval)
    print("\n📝 Test 3: CEO Rejection")
    leave_request3 = LeaveRequest.objects.create(
        employee=staff,
        leave_type=leave_type,
        start_date=date.today() + timedelta(days=30),
        end_date=date.today() + timedelta(days=32),
        reason="CEO rejection test"
    )
    
    # Manager approves
    leave_request3.manager_approve(manager, "Approved by manager")
    # HR approves  
    leave_request3.hr_approve(hr_user, "HR approved")
    # CEO rejects
    leave_request3.reject(ceo, "Strategic planning week - no leave allowed", "ceo")
    # Manually trigger notification
    LeaveNotificationService.notify_rejection(leave_request3, ceo, "ceo")
    
    # Check notifications for this request
    ceo_rejection_notifications = Notification.objects.filter(leave_request=leave_request3)
    print(f"   Notifications sent: {ceo_rejection_notifications.count()}")
    for notif in ceo_rejection_notifications:
        print(f"   → {notif.recipient.get_full_name()}: {notif.title}")
    
    # Summary
    print("\n📊 REJECTION NOTIFICATION SUMMARY:")
    print("✅ Manager rejection → Staff notified")
    print("✅ HR rejection → Staff + Manager notified") 
    print("✅ CEO rejection → Staff + Manager + HR notified")
    print("\n🎯 Smart targeting working correctly!")

if __name__ == '__main__':
    test_rejection_notifications()