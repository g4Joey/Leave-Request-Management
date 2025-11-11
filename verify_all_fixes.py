#!/usr/bin/env python
"""Comprehensive verification of all affiliate and CEO approval fixes."""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser as User, Affiliate
from users.serializers import UserSerializer, AffiliateSerializer
from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService

def test_user_serializer_fixes():
    """Test that UserSerializer now includes proper affiliate data."""
    print("=== USER SERIALIZER VERIFICATION ===")
    
    benjamin = User.objects.filter(email='ceo@umbcapital.com').first()
    if not benjamin:
        print("ERROR: Benjamin Ackah not found")
        return
    
    serializer = UserSerializer(benjamin)
    data = serializer.data
    
    print(f"Benjamin Ackah UserSerializer output:")
    print(f"  affiliate_id: {data.get('affiliate_id')} (should be 1)")
    print(f"  affiliate_name: {data.get('affiliate_name')} (should be 'MERBAN CAPITAL')")
    print(f"  affiliate: {data.get('affiliate')} (should be object with id and name)")
    
    # Test all CEOs
    ceos = User.objects.filter(role='ceo', is_active=True).order_by('affiliate__name')
    for ceo in ceos:
        serializer = UserSerializer(ceo)
        data = serializer.data
        affiliate_id = data.get('affiliate_id')
        affiliate_name = data.get('affiliate_name')
        
        status = "✅" if affiliate_id and affiliate_name else "❌"
        print(f"{status} {ceo.get_full_name()}: affiliate_id={affiliate_id}, affiliate_name='{affiliate_name}'")

def test_affiliate_serializer():
    """Test that AffiliateSerializer returns correct CEO data."""
    print("\n=== AFFILIATE SERIALIZER VERIFICATION ===")
    
    for affiliate in Affiliate.objects.all().order_by('name'):
        serializer = AffiliateSerializer(affiliate)
        data = serializer.data
        ceo = data.get('ceo')
        
        if ceo:
            status = "✅"
            print(f"{status} {affiliate.name}: CEO = {ceo['name']} ({ceo['email']})")
        else:
            status = "❌"
            print(f"{status} {affiliate.name}: No CEO data")

def test_staff_endpoint_structure():
    """Test that staff endpoints include all individual employees."""
    print("\n=== STAFF ENDPOINT VERIFICATION ===")
    
    from users.views import StaffManagementView
    from django.test import RequestFactory
    from django.contrib.auth.models import AnonymousUser
    
    factory = RequestFactory()
    
    for affiliate in Affiliate.objects.all().order_by('name'):
        # Simulate API call
        request = factory.get(f'/users/staff/?affiliate_id={affiliate.id}')
        request.user = AnonymousUser()
        
        view = StaffManagementView()
        view.request = request
        
        try:
            response = view.list(request)
            staff_data = response.data if hasattr(response, 'data') else []
            
            # Count CEOs in the response
            ceo_count = 0
            for item in staff_data:
                if isinstance(item, dict) and 'staff' in item:
                    for staff in item['staff']:
                        if staff.get('role') == 'ceo':
                            ceo_count += 1
                            print(f"✅ {affiliate.name}: Found CEO {staff.get('name')} in '{item.get('name')}' section")
            
            if ceo_count == 0:
                print(f"❌ {affiliate.name}: No CEO found in staff endpoint")
                
        except Exception as e:
            print(f"❌ {affiliate.name}: Error testing staff endpoint - {e}")

def test_ceo_approval_filtering():
    """Test that CEOs can see and approve requests from their affiliate only."""
    print("\n=== CEO APPROVAL FILTERING VERIFICATION ===")
    
    from leaves.views import LeaveRequestViewSet
    from django.test import RequestFactory
    from unittest.mock import Mock
    
    ceos = User.objects.filter(role='ceo', is_active=True)
    
    for ceo in ceos:
        print(f"\n{ceo.get_full_name()} ({ceo.affiliate}):")
        
        # Test if CEO can see requests
        factory = RequestFactory()
        request = factory.get('/leaves/')
        request.user = ceo
        
        view = LeaveRequestViewSet()
        view.request = request
        
        try:
            queryset = view.get_queryset()
            requests = queryset.all()
            
            print(f"  Can see {requests.count()} total requests")
            
            # Check if all requests are from CEO's affiliate
            for req in requests[:3]:  # Check first 3
                req_affiliate = None
                if req.employee.affiliate:
                    req_affiliate = req.employee.affiliate
                elif req.employee.department and req.employee.department.affiliate:
                    req_affiliate = req.employee.department.affiliate
                
                if req_affiliate == ceo.affiliate:
                    status = "✅"
                else:
                    status = "❌"
                
                print(f"    {status} Request {req.id}: {req.employee.get_full_name()} ({req_affiliate})")
                
                # Test if CEO can approve
                can_approve = ApprovalWorkflowService.can_user_approve(req, ceo)
                print(f"      Can approve: {can_approve} (status: {req.status})")
                
        except Exception as e:
            print(f"  ❌ Error testing CEO approval: {e}")

def test_frontend_api_endpoints():
    """Test the actual API endpoints that the frontend calls."""
    print("\n=== FRONTEND API ENDPOINTS VERIFICATION ===")
    
    from django.test import Client
    from django.contrib.auth import get_user_model
    import json
    
    User = get_user_model()
    
    # Get an admin user for testing
    admin_user = User.objects.filter(role__in=['admin', 'hr']).first()
    if not admin_user:
        print("❌ No admin user found for API testing")
        return
    
    client = Client()
    client.force_login(admin_user)
    
    # Test affiliates endpoint
    print("Testing /api/users/affiliates/:")
    response = client.get('/api/users/affiliates/')
    if response.status_code == 200:
        affiliates = response.json()
        for aff in affiliates:
            if aff.get('name') == 'MERBAN CAPITAL':
                ceo = aff.get('ceo')
                if ceo and ceo.get('name') == 'Benjamin Ackah':
                    print(f"  ✅ MERBAN CAPITAL CEO: {ceo['name']}")
                else:
                    print(f"  ❌ MERBAN CAPITAL CEO issue: {ceo}")
    else:
        print(f"  ❌ Affiliates endpoint failed: {response.status_code}")
    
    # Test staff endpoint for MERBAN
    print("Testing /api/users/staff/?affiliate_id=1:")
    response = client.get('/api/users/staff/?affiliate_id=1')
    if response.status_code == 200:
        staff_data = response.json()
        found_benjamin = False
        for item in staff_data:
            if isinstance(item, dict) and 'staff' in item:
                for staff in item['staff']:
                    if staff.get('email') == 'ceo@umbcapital.com':
                        found_benjamin = True
                        print(f"  ✅ Found Benjamin Ackah in '{item.get('name')}' section")
                        print(f"    Name: {staff.get('name')}")
                        print(f"    Affiliate: {staff.get('affiliate')}")
                        break
        if not found_benjamin:
            print("  ❌ Benjamin Ackah not found in staff endpoint")
    else:
        print(f"  ❌ Staff endpoint failed: {response.status_code}")

def main():
    """Run all verification tests."""
    print("COMPREHENSIVE VERIFICATION OF ALL FIXES")
    print("=" * 60)
    
    test_user_serializer_fixes()
    test_affiliate_serializer()
    test_staff_endpoint_structure()
    test_ceo_approval_filtering()
    test_frontend_api_endpoints()
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("\nIf all tests show ✅, the backend fixes are working correctly.")
    print("Frontend issues may require browser cache clear or dev server restart.")

if __name__ == "__main__":
    main()