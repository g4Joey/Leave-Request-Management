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
import requests

User = get_user_model()

def test_three_tier_flow():
    print("=== Testing Three-Tier Approval Flow ===")
    
    # Get users for testing
    manager = User.objects.filter(username='jmankoe').first()
    hr_user = User.objects.filter(role='hr').first()
    ceo_user = User.objects.filter(role='ceo').first()
    
    print(f"Manager: {manager.username if manager else 'NOT FOUND'}")
    print(f"HR User: {hr_user.username if hr_user else 'NOT FOUND'}")
    print(f"CEO User: {ceo_user.username if ceo_user else 'NOT FOUND'}")
    
    # Get the pending request
    pending_req = LeaveRequest.objects.filter(status='pending', employee__manager=manager).first()
    if not pending_req:
        print("ERROR: No pending requests found for manager's direct reports!")
        return
    
    print(f"\nTesting with request #{pending_req.pk}: {pending_req.employee.username} → {pending_req.leave_type.name}")
    print(f"Current status: {pending_req.status}")
    
    # Test the approval flow step by step
    print("\n=== Step 1: Manager Approval ===")
    print(f"Request should be status='pending' → status='manager_approved'")
    
    # Simulate manager approval
    try:
        pending_req.manager_approve(manager, "Approved by manager for testing")
        print(f"✓ Manager approved. New status: {pending_req.status}")
    except Exception as e:
        print(f"✗ Manager approval failed: {e}")
    
    if hr_user:
        print("\n=== Step 2: HR Approval ===")
        print(f"Request should be status='manager_approved' → status='hr_approved'")
        
        try:
            pending_req.hr_approve(hr_user, "Approved by HR for testing")
            print(f"✓ HR approved. New status: {pending_req.status}")
        except Exception as e:
            print(f"✗ HR approval failed: {e}")
    
    if ceo_user:
        print("\n=== Step 3: CEO Final Approval ===")
        print(f"Request should be status='hr_approved' → status='approved'")
        
        try:
            pending_req.ceo_approve(ceo_user, "Final approval by CEO for testing")
            print(f"✓ CEO approved. New status: {pending_req.status}")
        except Exception as e:
            print(f"✗ CEO approval failed: {e}")
    
    print(f"\nFinal request status: {pending_req.status}")
    
    # Reset for actual testing
    print("\n=== Resetting Request for Live Testing ===")
    pending_req.status = 'pending'
    pending_req.manager_approved_by = None
    pending_req.manager_approval_date = None
    pending_req.manager_approval_comments = ""
    pending_req.hr_approved_by = None
    pending_req.hr_approval_date = None
    pending_req.hr_approval_comments = ""
    pending_req.ceo_approved_by = None
    pending_req.ceo_approval_date = None
    pending_req.ceo_approval_comments = ""
    pending_req.save()
    
    print(f"✓ Request #{pending_req.pk} reset to status='pending' for live testing")
    print("\nNow you can test the Manager tab UI:")
    print("1. Log in as jmankoe")
    print("2. Go to Manager tab")
    print("3. Click the green 'Approve' button")
    print("4. Request should move to HR stage")

if __name__ == '__main__':
    test_three_tier_flow()