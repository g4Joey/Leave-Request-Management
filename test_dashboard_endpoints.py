#!/usr/bin/env python3
"""
Test dashboard API endpoints
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from leaves.views import LeaveRequestViewSet, LeaveBalanceViewSet
from rest_framework.test import force_authenticate

def test_dashboard_endpoints():
    print("=== Testing Dashboard API Endpoints ===")
    
    User = get_user_model()
    user = User.objects.get(username='aakorfu')
    factory = RequestFactory()
    
    print(f"\nTesting for user: {user.username}")
    
    # Test leave balances endpoint
    print("\n1. Testing /leaves/balances/current_year_full/")
    request = factory.get('/leaves/balances/current_year_full/')
    force_authenticate(request, user=user)
    view = LeaveBalanceViewSet.as_view({'get': 'current_year_full'})
    response = view(request)
    print(f"   Status: {response.status_code}")
    print(f"   Data count: {len(response.data)}")
    if response.data:
        print(f"   Sample balance: {response.data[0]}")
    
    # Test recent requests endpoint  
    print("\n2. Testing /leaves/requests/ (recent requests)")
    request = factory.get('/leaves/requests/')
    force_authenticate(request, user=user)
    view = LeaveRequestViewSet.as_view({'get': 'list'})
    response = view(request)
    print(f"   Status: {response.status_code}")
    
    if isinstance(response.data, dict) and 'results' in response.data:
        data = response.data['results']
        print(f"   Data type: Paginated results")
        print(f"   Count: {len(data)}")
    elif isinstance(response.data, list):
        data = response.data
        print(f"   Data type: List")
        print(f"   Count: {len(data)}")
    else:
        data = []
        print(f"   Data type: {type(response.data)}")
        print(f"   Response: {response.data}")
    
    if data:
        print(f"   Sample request: {data[0]}")
    
    # Test dashboard endpoint (not used by frontend but let's check)
    print("\n3. Testing /leaves/requests/dashboard/")
    request = factory.get('/leaves/requests/dashboard/')
    force_authenticate(request, user=user)
    view = LeaveRequestViewSet.as_view({'get': 'dashboard'})
    response = view(request)
    print(f"   Status: {response.status_code}")
    print(f"   Data: {response.data}")

if __name__ == '__main__':
    test_dashboard_endpoints()