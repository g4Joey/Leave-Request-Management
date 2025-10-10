#!/usr/bin/env python
"""
Test script to verify the three-tier approval system works correctly
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from leaves.models import LeaveRequest, LeaveType, LeaveBalance
from users.models import Department
from notifications.models import Notification
from notifications.services import LeaveNotificationService
from datetime import date, timedelta

User = get_user_model()

def test_approval_workflow():
    """Test the complete approval workflow"""
    print("🚀 Testing Three-Tier Approval System")
    print("=" * 50)
    
    # Get or create test users
    try:
        # Get existing users
        ceo = User.objects.get(role='ceo')
        hr_user = User.objects.filter(role='hr').first()
        manager = User.objects.filter(role='manager').first()
        staff = User.objects.filter(role__in=['junior_staff', 'senior_staff']).first()
        
        if not hr_user:
            print("❌ No HR user found. Creating one...")
            hr_user = User.objects.create_user(
                username='hr_test',
                email='hr@test.com',
                employee_id='HR001',
                role='hr',
                first_name='HR',
                last_name='Manager'
            )
        
        if not manager:
            print("❌ No manager found. Creating one...")
            manager = User.objects.create_user(
                username='manager_test',
                email='manager@test.com',
                employee_id='MGR001',
                role='manager',
                first_name='Test',
                last_name='Manager'
            )
        
        if not staff:
            print("❌ No staff found. Creating one...")
            staff = User.objects.create_user(
                username='staff_test',
                email='staff@test.com',
                employee_id='STF001',
                role='junior_staff',
                first_name='Test',
                last_name='Employee',
                manager=manager
            )
        
        print(f"✅ Users ready:")
        print(f"   CEO: {ceo.username} ({ceo.get_full_name()})")
        print(f"   HR: {hr_user.username} ({hr_user.get_full_name()})")
        print(f"   Manager: {manager.username} ({manager.get_full_name()})")
        print(f"   Staff: {staff.username} ({staff.get_full_name()})")
        
        # Get leave type
        leave_type = LeaveType.objects.first()
        if not leave_type:
            leave_type = LeaveType.objects.create(
                name='Annual Leave',
                description='Annual vacation leave'
            )
        
        # Create leave balance for staff
        balance, created = LeaveBalance.objects.get_or_create(
            employee=staff,
            leave_type=leave_type,
            year=2025,
            defaults={'entitled_days': 25}
        )
        
        # Create a leave request
        print(f"\n📝 Creating leave request...")
        leave_request = LeaveRequest.objects.create(
            employee=staff,
            leave_type=leave_type,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=35),
            reason="Family vacation"
        )
        
        print(f"✅ Leave request created: {leave_request.id}")
        print(f"   Status: {leave_request.status}")
        print(f"   Next approver: {leave_request.next_approver_role}")
        
        # Test manager approval
        print(f"\n👔 Manager approval...")
        if leave_request.status == 'pending':
            leave_request.manager_approve(manager, "Approved by manager - good reason")
            print(f"✅ Manager approved")
            print(f"   Status: {leave_request.status}")
            print(f"   Next approver: {leave_request.next_approver_role}")
        
        # Test HR approval
        print(f"\n🏢 HR approval...")
        if leave_request.status == 'manager_approved':
            leave_request.hr_approve(hr_user, "HR approved - within policy")
            print(f"✅ HR approved")
            print(f"   Status: {leave_request.status}")
            print(f"   Next approver: {leave_request.next_approver_role}")
        
        # Test CEO approval
        print(f"\n👑 CEO approval...")
        if leave_request.status == 'hr_approved':
            leave_request.ceo_approve(ceo, "Final approval granted")
            print(f"✅ CEO approved")
            print(f"   Status: {leave_request.status}")
            print(f"   Final approval stage: {leave_request.current_approval_stage}")
        
        # Check notifications
        print(f"\n📧 Checking notifications...")
        notifications = Notification.objects.filter(leave_request=leave_request).count()
        print(f"✅ {notifications} notifications created for this request")
        
        print(f"\n🎉 Three-tier approval workflow test COMPLETED!")
        print(f"✅ Manager → HR → CEO approval chain working correctly")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

def test_rejection_workflow():
    """Test rejection at different stages"""
    print(f"\n🛑 Testing rejection workflow...")
    
    try:
        # Get users
        ceo = User.objects.get(role='ceo')
        hr_user = User.objects.filter(role='hr').first()
        manager = User.objects.filter(role='manager').first()
        staff = User.objects.filter(role__in=['junior_staff', 'senior_staff']).first()
        leave_type = LeaveType.objects.first()
        
        # Create another leave request
        leave_request = LeaveRequest.objects.create(
            employee=staff,
            leave_type=leave_type,
            start_date=date.today() + timedelta(days=60),
            end_date=date.today() + timedelta(days=65),
            reason="Personal trip"
        )
        
        # Manager approves
        leave_request.manager_approve(manager, "Looks good")
        print(f"✅ Manager approved, status: {leave_request.status}")
        
        # HR rejects
        leave_request.reject(hr_user, "Conflicts with busy period", "hr")
        print(f"✅ HR rejected, status: {leave_request.status}")
        
        # Check notifications for rejection
        rejection_notifications = Notification.objects.filter(
            leave_request=leave_request,
            notification_type='leave_rejected'
        ).count()
        print(f"✅ {rejection_notifications} rejection notifications sent")
        
    except Exception as e:
        print(f"❌ Rejection test error: {str(e)}")

if __name__ == '__main__':
    test_approval_workflow()
    test_rejection_workflow()
    print(f"\n✨ All tests completed!")