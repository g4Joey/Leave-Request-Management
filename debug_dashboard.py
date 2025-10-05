#!/usr/bin/env python
"""Debug script to check dashboard API responses"""

import os
import sys
import django

# Setup Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.views import LeaveBalanceViewSet, LeaveRequestViewSet
from users.models import CustomUser
from unittest.mock import Mock

def test_user_dashboard(username):
    print(f"\n=== TESTING DASHBOARD FOR {username} ===")
    
    try:
        user = CustomUser.objects.get(username=username)
        print(f"User: {user.get_full_name()} ({user.username})")
        print(f"Role: {user.role}")
        
        # Test balance endpoint
        request = Mock()
        request.user = user
        
        balance_viewset = LeaveBalanceViewSet()
        balance_viewset.request = request
        balance_response = balance_viewset.current_year_full(request)
        
        print(f"Balance API response count: {len(balance_response.data)}")
        for item in balance_response.data:
            leave_type_name = item.get('leave_type', {}).get('name', 'Unknown')
            entitled = item.get('entitled_days', 0)
            remaining = item.get('remaining_days', 0)
            print(f"  {leave_type_name}: {entitled} entitled, {remaining} remaining")
        
        # Test recent requests
        request_viewset = LeaveRequestViewSet()
        request_viewset.request = request
        
        # Get recent requests (same as dashboard does)
        recent_requests = request_viewset.get_queryset().order_by('-created_at')[:5]
        print(f"\nRecent requests count: {recent_requests.count()}")
        for req in recent_requests:
            print(f"  {req.leave_type.name}: {req.start_date} to {req.end_date} ({req.status})")
            
    except Exception as e:
        print(f"Error testing {username}: {e}")

if __name__ == '__main__':
    test_user_dashboard('jmankoe')
    test_user_dashboard('admin@company.com')