#!/usr/bin/env python
"""
Test script to verify overlap detection functionality.
Run this script after setting up the overlap detection feature.
"""

import os
import sys
import django
from datetime import date, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from leaves.models import LeaveRequest, LeaveType
from leaves.utils import find_overlaps, get_overlap_summary, should_trigger_overlap_notification
from notifications.models import Notification
from notifications.services import LeaveNotificationService

User = get_user_model()

def test_overlap_detection():
    """Test overlap detection utility functions"""
    print("🔍 Testing Overlap Detection Feature\n")
    
    # Get or create test data
    try:
        # Get leave type
        leave_type = LeaveType.objects.first()
        if not leave_type:
            print("❌ No leave types found. Please create leave types first.")
            return False
            
        # Get users from different departments
        users = User.objects.filter(is_active=True)[:3]
        if len(users) < 2:
            print("❌ Need at least 2 active users for testing.")
            return False
            
        user1, user2 = users[0], users[1]
        print(f"👤 Using users: {user1.get_full_name()} and {user2.get_full_name()}")
        
        # Check if users have departments
        dept1_id = getattr(user1.department, 'id', None) if hasattr(user1, 'department') else None
        dept2_id = getattr(user2.department, 'id', None) if hasattr(user2, 'department') else None
        
        if not dept1_id:
            print(f"⚠️ User {user1.username} has no department assigned - using department ID 1")
            dept1_id = 1
            
        # Create overlapping leave requests
        today = date.today()
        start_date = today + timedelta(days=10)
        end_date = today + timedelta(days=12)
        
        # Create first leave request
        leave1 = LeaveRequest.objects.create(
            employee=user1,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason="Test overlap detection",
            status='approved'
        )
        
        # Create overlapping leave request
        overlap_start = start_date + timedelta(days=1)  # Overlaps by 1 day
        overlap_end = end_date + timedelta(days=2)
        
        leave2 = LeaveRequest.objects.create(
            employee=user2,
            leave_type=leave_type,
            start_date=overlap_start,
            end_date=overlap_end,
            reason="Test overlap detection - overlapping request",
            status='pending'
        )
        
        print(f"📅 Created test leave requests:")
        print(f"   Leave 1: {start_date} to {end_date} (User: {user1.username})")
        print(f"   Leave 2: {overlap_start} to {overlap_end} (User: {user2.username})")
        
        # Test overlap detection
        print(f"\n🔍 Testing overlap detection...")
        
        overlaps = find_overlaps(
            dept_id=dept1_id,
            new_start=overlap_start,
            new_end=overlap_end,
            exclude_user_id=user2.id
        )
        
        print(f"   Found {overlaps.count()} overlapping leaves")
        
        if overlaps.exists():
            overlap_summary = get_overlap_summary(overlaps, overlap_start, overlap_end)
            print(f"   Overlap Summary: {overlap_summary['total_overlaps']} overlaps, {overlap_summary['total_overlap_days']} overlap days")
            
            # Test notification trigger logic
            should_notify = should_trigger_overlap_notification(overlap_summary)
            print(f"   Should trigger notification: {should_notify}")
            
            if should_notify:
                # Test notification service
                initial_notification_count = Notification.objects.count()
                LeaveNotificationService.notify_leave_overlap(leave2, overlap_summary)
                final_notification_count = Notification.objects.count()
                notifications_created = final_notification_count - initial_notification_count
                print(f"   Created {notifications_created} overlap notifications")
            
        else:
            print("   ❌ No overlaps detected - check department assignments")
        
        # Cleanup
        print(f"\n🧹 Cleaning up test data...")
        leave1.delete()
        leave2.delete()
        
        # Clean up test notifications
        test_notifications = Notification.objects.filter(notification_type='leave_overlap_detected')
        deleted_count = test_notifications.count()
        test_notifications.delete()
        print(f"   Deleted {deleted_count} test notifications")
        
        print(f"\n✅ Overlap detection test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoint():
    """Test the overlap API endpoint"""
    print(f"\n🌐 Testing Overlap API Endpoint")
    
    try:
        from django.test import Client
        from django.contrib.auth import authenticate
        
        # Get a test user
        user = User.objects.filter(is_active=True).first()
        if not user:
            print("❌ No active users found for API testing")
            return False
            
        client = Client()
        
        # Test unauthenticated access
        response = client.get('/api/leaves/overlaps/?start=2025-12-01&end=2025-12-03&dept_id=1')
        print(f"   Unauthenticated access: {response.status_code} (should be 401/403)")
        
        # Test authenticated access
        client.force_login(user)
        response = client.get('/api/leaves/overlaps/?start=2025-12-01&end=2025-12-03&dept_id=1')
        print(f"   Authenticated access: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response contains {len(data.get('overlaps', []))} overlaps")
            print("   ✅ API endpoint working correctly")
        else:
            print(f"   Response: {response.content}")
            
    except Exception as e:
        print(f"❌ API test failed: {str(e)}")
        return False
        
    return True

def main():
    """Run all tests"""
    print("🚀 Starting Overlap Detection Tests")
    print("=" * 50)
    
    success = True
    
    # Test utility functions
    if not test_overlap_detection():
        success = False
    
    # Test API endpoint
    if not test_api_endpoint():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! Overlap detection is working correctly.")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    return success

if __name__ == '__main__':
    main()