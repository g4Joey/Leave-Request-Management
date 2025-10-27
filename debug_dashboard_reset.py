#!/usr/bin/env python
"""
Test script to debug dashboard and admin reset issues
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from leaves.models import LeaveRequest, LeaveBalance, LeaveType
from leaves.views import ManagerLeaveViewSet, LeaveBalanceViewSet
from django.test import RequestFactory
from rest_framework.test import force_authenticate
import json

def test_dashboard_data():
    print("=== TESTING DASHBOARD DATA ===")
    
    # Get a regular user
    user = CustomUser.objects.filter(is_active=True, role__in=['staff', 'junior_staff', 'senior_staff']).first()
    if not user:
        user = CustomUser.objects.filter(is_active=True).first()
    
    print(f"Testing with user: {user.username} (role: {getattr(user, 'role', 'None')})")
    
    # Test balances endpoint
    factory = RequestFactory()
    request = factory.get('/api/leaves/balances/current_year_full/')
    force_authenticate(request, user=user)
    
    viewset = LeaveBalanceViewSet()
    viewset.request = request
    # Set up request properly
    request.user = user
    response = viewset.current_year_full(request)
    
    print(f"Balances endpoint status: {response.status_code}")
    print(f"Balances data type: {type(response.data)}")
    print(f"Balances data length: {len(response.data) if hasattr(response.data, '__len__') else 'N/A'}")
    
    if response.data and len(response.data) > 0:
        first_item = response.data[0]
        print(f"First item: {json.dumps(first_item, indent=2)}")
        print(f"leave_type field: {first_item.get('leave_type')}")
        print(f"leave_type.name: {first_item.get('leave_type', {}).get('name', 'MISSING')}")
    else:
        print("No data returned!")

def test_admin_reset():
    print("\n=== TESTING ADMIN RESET ===")
    
    # Get admin user
    admin_user = CustomUser.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = CustomUser.objects.filter(role='admin').first()
    
    if not admin_user:
        print("No admin user found!")
        return
    
    print(f"Admin user: {admin_user.username}")
    print(f"Is superuser: {getattr(admin_user, 'is_superuser', False)}")
    print(f"Role: {getattr(admin_user, 'role', 'None')}")
    
    # Check current counts
    requests_before = LeaveRequest.objects.count()
    balances_before = LeaveBalance.objects.count()
    print(f"Requests before: {requests_before}")
    print(f"Balances before: {balances_before}")
    
    # Test system reset
    factory = RequestFactory()
    request_data = {'confirm_reset': 'yes, reset everything'}
    request = factory.post('/api/leaves/manager/system_reset/', 
                          data=json.dumps(request_data), 
                          content_type='application/json')
    force_authenticate(request, user=admin_user)
    
    # Parse the JSON data into request.data manually for testing
    import io
    from django.http import QueryDict
    request.data = request_data
    
    viewset = ManagerLeaveViewSet()
    viewset.request = request
    # Set up request properly
    request.user = admin_user
    
    try:
        response = viewset.system_reset(request)
        print(f"Reset response status: {response.status_code}")
        if hasattr(response, 'data'):
            print(f"Reset response: {json.dumps(response.data, indent=2)}")
            
        # Check counts after
        requests_after = LeaveRequest.objects.count()
        balances_after = LeaveBalance.objects.count()
        print(f"Requests after: {requests_after}")
        print(f"Balances after: {balances_after}")
        
        # Check if balances were actually reset (used/pending should be 0)
        sample_balance = LeaveBalance.objects.first()
        if sample_balance:
            print(f"Sample balance after reset: used={sample_balance.used_days}, pending={sample_balance.pending_days}")
    except Exception as e:
        print(f"Error during reset: {str(e)}")

if __name__ == "__main__":
    test_dashboard_data()
    test_admin_reset()