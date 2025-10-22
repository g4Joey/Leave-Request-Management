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
from leaves.views import ManagerLeaveViewSet
from django.test import RequestFactory
from rest_framework.test import force_authenticate

User = get_user_model()

def test_manager_flow():
    print("=== Testing Manager Flow for IT Department ===")
    
    # Get jmankoe (manager)
    manager = User.objects.filter(username='jmankoe').first()
    if not manager:
        print("ERROR: Manager jmankoe not found!")
        return
    
    print(f"Manager: {manager.username} (role: {manager.role}, dept: {getattr(manager.department, 'name', None)})")
    
    # Get pending requests for his direct reports
    pending = LeaveRequest.objects.filter(
        status='pending',
        employee__manager=manager
    ).select_related('employee', 'leave_type')
    
    print(f"Pending requests for direct reports: {pending.count()}")
    for req in pending:
        print(f"  - Request #{req.pk}: {req.employee.username} → {req.leave_type.name} ({req.start_date} to {req.end_date})")
    
    # Test API endpoint
    factory = RequestFactory()
    request = factory.get('/api/leaves/manager/pending_approvals/')
    
    # Test the ViewSet
    viewset = ManagerLeaveViewSet()
    viewset.request = request
    request.user = manager
    
    # Test queryset
    qs = viewset.get_queryset()
    print(f"Manager queryset count: {qs.count()}")
    
    # Test pending_approvals action
    try:
        response = viewset.pending_approvals(request)
        data = response.data
        print(f"Pending approvals API response:")
        print(f"  - Count: {data.get('count', 0)}")
        print(f"  - User role: {data.get('user_role')}")
        print(f"  - Requests: {len(data.get('requests', []))}")
        
        for req in data.get('requests', []):
            print(f"    * {req.get('employee_name')} - {req.get('leave_type_name')} ({req.get('start_date')} to {req.get('end_date')})")
    except Exception as e:
        print(f"ERROR in pending_approvals: {e}")
    
    print("\n=== Next Steps ===")
    print("1. Log in as jmankoe")
    print("2. Go to Manager tab")
    print("3. You should see pending requests with green Approve and red Reject buttons")
    print("4. Test the three-tier flow: Manager → HR → CEO")

if __name__ == '__main__':
    test_manager_flow()