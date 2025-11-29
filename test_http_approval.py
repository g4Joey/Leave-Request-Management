#!/usr/bin/env python
"""
Test the full HTTP approval flow to see where it fails.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

# Configure logging
import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

from django.test import RequestFactory
from users.models import CustomUser
from leaves.models import LeaveRequest
from leaves.views import ManagerLeaveViewSet
from rest_framework.test import force_authenticate

def test_http_approval(lr_id, ceo_email):
    """Test the HTTP approval flow."""
    print(f"\n{'='*80}")
    print(f"Testing HTTP Approval for LR#{lr_id} by {ceo_email}")
    print(f"{'='*80}")
    
    try:
        lr = LeaveRequest.objects.get(id=lr_id)
        ceo = CustomUser.objects.get(email=ceo_email)
        
        print(f"\nLeave Request: #{lr.id}")
        print(f"  Employee: {lr.employee.get_full_name()}")
        print(f"  Status: {lr.status}")
        
        print(f"\nCEO: {ceo.get_full_name()}")
        print(f"  Role: {ceo.role}")
        print(f"  Affiliate: {getattr(ceo.affiliate, 'name', 'None') if ceo.affiliate else 'None'}")
        
        # Create a request
        factory = RequestFactory()
        request = factory.put(f'/api/leaves/manager/{lr_id}/approve/', {
            'approval_comments': 'Test approval'
        }, content_type='application/json')
        
        # Force authenticate as the CEO
        force_authenticate(request, user=ceo)
        
        # Create viewset and call approve action
        viewset = ManagerLeaveViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        print(f"\nCalling approve action...")
        response = viewset.approve(request, pk=lr_id)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Data: {response.data}")
        
        if response.status_code == 200:
            print("\n[SUCCESS] Approval succeeded")
        else:
            print(f"\n[FAILED] Approval failed with status {response.status_code}")
            
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

def main():
    # Test the most problematic case
    test_http_approval(49, 'ceo@umbcapital.com')  # Joseph Mankoe's request
    test_http_approval(54, 'sdslceo@umbcapital.com')  # SDSL request

if __name__ == '__main__':
    main()
