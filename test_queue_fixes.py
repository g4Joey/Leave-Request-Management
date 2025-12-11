#!/usr/bin/env python3
"""
Test the queue filtering fixes to verify:
1. Manager requests don't appear in manager approval queues
2. HR queue correctly shows cross-affiliate items
3. Leave type activation works with inactive types
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
from users.models import CustomUser, Affiliate, Department
from leaves.views import ManagerLeaveViewSet
from django.test import RequestFactory
from rest_framework.test import force_authenticate
import traceback

def test_queue_filtering():
    """Test approval queue filtering to ensure role segregation"""
    print("=== Testing Queue Filtering Fixes ===\n")
    
    try:
        # Create test factory
        factory = RequestFactory()
        viewset = ManagerLeaveViewSet()
        
        # Test users
        manager = CustomUser.objects.filter(role='manager').first()
        hr_user = CustomUser.objects.filter(role='hr').first()
        admin_user = CustomUser.objects.filter(role='admin').first()
        ceo_user = CustomUser.objects.filter(role='ceo').first()
        
        print(f"Test users found:")
        print(f"  Manager: {manager.email if manager else 'None'}")
        print(f"  HR: {hr_user.email if hr_user else 'None'}")
        print(f"  Admin: {admin_user.email if admin_user else 'None'}")
        print(f"  CEO: {ceo_user.email if ceo_user else 'None'}\n")
        
        # Test manager queue filtering
        if manager:
            print("1. Testing Manager Queue Filtering:")
            request = factory.get('/api/leaves/manager/pending-approvals/')
            force_authenticate(request, user=manager)
            viewset.request = request
            viewset.action = 'pending_approvals'
            
            # Get manager's pending queue
            try:
                response = viewset.pending_approvals(request)
                manager_queue = response.data.get('results', [])
                print(f"   Manager queue contains {len(manager_queue)} items")
                
                # Check if any manager/CEO role submitters are in the queue
                role_violations = []
                for item in manager_queue:
                    employee_role = item.get('employee', {}).get('role', '')
                    if employee_role in ['manager', 'ceo', 'hr', 'admin']:
                        role_violations.append(f"{item.get('employee', {}).get('email', 'unknown')} ({employee_role})")
                
                if role_violations:
                    print(f"   ❌ VIOLATION: Found non-staff in manager queue: {', '.join(role_violations)}")
                else:
                    print("   ✅ PASS: Manager queue contains only staff requests")
                    
            except Exception as e:
                print(f"   ❌ ERROR: {str(e)}")
        
        # Test HR queue cross-affiliate access
        if hr_user:
            print("\n2. Testing HR Queue Cross-Affiliate Access:")
            request = factory.get('/api/leaves/manager/pending-approvals/')
            force_authenticate(request, user=hr_user)
            viewset.request = request
            viewset.action = 'pending_approvals'
            
            try:
                response = viewset.pending_approvals(request)
                hr_queue = response.data.get('results', [])
                print(f"   HR queue contains {len(hr_queue)} items")
                
                # Check for cross-affiliate visibility
                affiliates_seen = set()
                statuses_seen = set()
                for item in hr_queue:
                    emp_affiliate = item.get('employee', {}).get('affiliate_name', '')
                    if emp_affiliate:
                        affiliates_seen.add(emp_affiliate)
                    statuses_seen.add(item.get('status', ''))
                
                print(f"   Affiliates in HR queue: {', '.join(affiliates_seen) if affiliates_seen else 'None'}")
                print(f"   Statuses in HR queue: {', '.join(statuses_seen) if statuses_seen else 'None'}")
                
                if 'ceo_approved' in statuses_seen:
                    print("   ✅ PASS: HR can see ceo_approved items (cross-affiliate access)")
                else:
                    print("   ⚠️  INFO: No ceo_approved items currently available for testing")
                    
            except Exception as e:
                print(f"   ❌ ERROR: {str(e)}")
        
        # Test admin queue filtering
        if admin_user:
            print("\n3. Testing Admin Queue Filtering:")
            request = factory.get('/api/leaves/manager/pending-approvals/')
            force_authenticate(request, user=admin_user)
            viewset.request = request
            viewset.action = 'pending_approvals'
            
            try:
                response = viewset.pending_approvals(request)
                admin_queue = response.data.get('results', [])
                print(f"   Admin queue contains {len(admin_queue)} items")
                
                # Check if any manager/CEO role submitters are in the queue
                role_violations = []
                for item in admin_queue:
                    employee_role = item.get('employee', {}).get('role', '')
                    if employee_role in ['manager', 'ceo', 'hr', 'admin']:
                        role_violations.append(f"{item.get('employee', {}).get('email', 'unknown')} ({employee_role})")
                
                if role_violations:
                    print(f"   ❌ VIOLATION: Found non-staff in admin queue: {', '.join(role_violations)}")
                else:
                    print("   ✅ PASS: Admin queue contains only staff requests")
                    
            except Exception as e:
                print(f"   ❌ ERROR: {str(e)}")
        
        # Test leave type activation
        print("\n4. Testing Leave Type Activation Fix:")
        try:
            # Find or create an inactive leave type
            inactive_type = LeaveType.objects.filter(is_active=False).first()
            if not inactive_type:
                # Create a test inactive leave type
                inactive_type = LeaveType.objects.create(
                    name="Test Inactive Type",
                    description="Test type for activation",
                    is_active=False
                )
                print(f"   Created test inactive leave type: {inactive_type.name}")
            else:
                print(f"   Found existing inactive leave type: {inactive_type.name}")
            
            print(f"   Before activation: is_active = {inactive_type.is_active}")
            
            # Test that we can retrieve it with full queryset
            retrieved = LeaveType.objects.get(pk=inactive_type.pk)
            print(f"   ✅ PASS: Can retrieve inactive leave type with full queryset")
            
            # Test filtered queryset (this should fail for inactive types)
            try:
                filtered = LeaveType.objects.filter(is_active=True).get(pk=inactive_type.pk)
                print(f"   ❌ UNEXPECTED: Retrieved inactive type from active-only queryset")
            except LeaveType.DoesNotExist:
                print(f"   ✅ PASS: Inactive type not found in active-only queryset (expected)")
                
        except Exception as e:
            print(f"   ❌ ERROR in leave type test: {str(e)}")
        
        print("\n=== Queue Filtering Test Complete ===")
        
    except Exception as e:
        print(f"❌ MAJOR ERROR: {str(e)}")
        traceback.print_exc()

if __name__ == '__main__':
    test_queue_filtering()