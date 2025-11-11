#!/usr/bin/env python
"""Comprehensive CEO approval diagnostic based on user's troubleshooting tips."""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Affiliate, CustomUser
from leaves.models import LeaveRequest
from django.db.models import Q

User = get_user_model()

def check_ceo_affiliate_data():
    """1. Quick data checks — verify CEOs and affiliates"""
    print("=== 1. CEO AND AFFILIATE DATA VERIFICATION ===")
    
    merban = Affiliate.objects.filter(name__iexact='MERBAN CAPITAL').first()
    print(f"Merban affiliate: {merban} (ID: {merban.id if merban else None})")
    
    print("\nCEO users:")
    for u in User.objects.filter(role__iexact='ceo'):
        affiliate = getattr(u, 'affiliate', None)
        department = getattr(u, 'department', None)
        print(f"  CEO: {u.email}")
        print(f"    affiliate: {affiliate}")
        print(f"    department: {department}")
        print(f"    department.affiliate: {department.affiliate if department else None}")
        
        # Check if this is Benjamin and if he lacks affiliate
        if 'ceo@umbcapital.com' in u.email.lower() or 'benjamin' in u.get_full_name().lower():
            if not affiliate:
                print(f"    ❌ PROBLEM: Benjamin has no affiliate set!")
                return u, merban
            else:
                print(f"    ✅ Benjamin has affiliate: {affiliate}")
    
    return None, merban

def fix_benjamin_affiliate(benjamin_user, merban_affiliate):
    """2. Fix CEO affiliate if missing"""
    if benjamin_user and merban_affiliate:
        print(f"\n=== 2. FIXING BENJAMIN'S AFFILIATE ===")
        print(f"Setting affiliate for {benjamin_user.email} to {merban_affiliate}")
        benjamin_user.affiliate = merban_affiliate
        benjamin_user.save()
        print(f"✅ Saved: {benjamin_user} -> affiliate: {benjamin_user.affiliate}")
        return True
    return False

def check_approval_queue_filtering():
    """3. Verify approval-queue filtering logic"""
    print(f"\n=== 3. APPROVAL QUEUE FILTERING VERIFICATION ===")
    
    # Test the current CEO queryset filtering
    benjamin = User.objects.filter(email='ceo@umbcapital.com').first()
    if not benjamin:
        print("❌ Benjamin not found")
        return
    
    print(f"Testing approval queue for Benjamin: {benjamin.email}")
    print(f"  Benjamin's affiliate: {benjamin.affiliate}")
    print(f"  Benjamin's department: {benjamin.department}")
    
    # Check what leave requests should be visible to Benjamin
    if benjamin.affiliate:
        affiliate = benjamin.affiliate
        
        # Test different filtering approaches
        print(f"\n  Testing queryset filters for affiliate: {affiliate}")
        
        # Method 1: Current implementation (from leaves/views.py)
        current_qs = LeaveRequest.objects.filter(
            Q(employee__affiliate=affiliate) | Q(employee__department__affiliate=affiliate)
        ).filter(status__in=['pending', 'hr_approved', 'ceo_approved', 'approved', 'rejected'])
        
        print(f"  Current filtering (from views.py): {current_qs.count()} requests")
        for req in current_qs:
            print(f"    - Request {req.id}: {req.employee.get_full_name()} ({req.status})")
        
        # Method 2: More robust filtering 
        robust_qs = LeaveRequest.objects.filter(
            status='hr_approved'
        ).filter(
            Q(employee__department__affiliate=affiliate) |
            Q(employee__affiliate=affiliate) |
            Q(employee__department__affiliate__id=affiliate.id) |
            Q(employee__affiliate__id=affiliate.id)
        ).distinct()
        
        print(f"  Robust filtering (hr_approved only): {robust_qs.count()} requests")
        for req in robust_qs:
            print(f"    - Request {req.id}: {req.employee.get_full_name()} ({req.status})")
            
        # Method 3: Check specific request mentioned by user
        augustine_req = LeaveRequest.objects.filter(employee__email__icontains='akorfu').first()
        if augustine_req:
            print(f"\n  Augustine's request (ID {augustine_req.id}):")
            print(f"    Employee: {augustine_req.employee.get_full_name()}")
            print(f"    Employee affiliate: {augustine_req.employee.affiliate}")
            print(f"    Employee department: {augustine_req.employee.department}")
            print(f"    Employee dept affiliate: {augustine_req.employee.department.affiliate if augustine_req.employee.department else None}")
            print(f"    Status: {augustine_req.status}")
            
            # Test if this request should be visible to Benjamin
            matches_current = current_qs.filter(id=augustine_req.id).exists()
            matches_robust = robust_qs.filter(id=augustine_req.id).exists()
            print(f"    Matches current filter: {matches_current}")
            print(f"    Matches robust filter: {matches_robust}")

def check_leave_request_viewset_logic():
    """4. Check the actual LeaveRequestViewSet logic"""
    print(f"\n=== 4. LEAVEREQUESTVIEWSET LOGIC CHECK ===")
    
    from leaves.views import LeaveRequestViewSet
    from django.test import RequestFactory
    from unittest.mock import Mock
    
    # Simulate a request from Benjamin
    benjamin = User.objects.filter(email='ceo@umbcapital.com').first()
    if not benjamin:
        print("❌ Benjamin not found")
        return
        
    factory = RequestFactory()
    request = factory.get('/api/leaves/')
    request.user = benjamin
    
    viewset = LeaveRequestViewSet()
    viewset.request = request
    
    try:
        # Test the get_queryset method
        queryset = viewset.get_queryset()
        print(f"LeaveRequestViewSet.get_queryset() for Benjamin:")
        print(f"  Total requests: {queryset.count()}")
        
        for req in queryset:
            print(f"    - Request {req.id}: {req.employee.get_full_name()} ({req.status})")
            
    except Exception as e:
        print(f"❌ Error testing LeaveRequestViewSet: {e}")

def check_ceo_approval_routing():
    """5. Test ApprovalRoutingService.get_ceo_for_employee"""
    print(f"\n=== 5. CEO APPROVAL ROUTING CHECK ===")
    
    from leaves.services import ApprovalRoutingService
    
    # Test with Augustine's request
    augustine = User.objects.filter(email__icontains='akorfu').first()
    if augustine:
        print(f"Testing CEO routing for Augustine: {augustine.get_full_name()}")
        print(f"  Augustine's affiliate: {augustine.affiliate}")
        print(f"  Augustine's department: {augustine.department}")
        print(f"  Augustine's dept affiliate: {augustine.department.affiliate if augustine.department else None}")
        
        expected_ceo = ApprovalRoutingService.get_ceo_for_employee(augustine)
        print(f"  Expected CEO: {expected_ceo}")
        
        if expected_ceo:
            print(f"  Expected CEO affiliate: {expected_ceo.affiliate}")
        else:
            print("  ❌ No CEO found for Augustine!")

def main():
    """Run all diagnostics"""
    print("COMPREHENSIVE CEO APPROVAL DIAGNOSTIC")
    print("=" * 60)
    
    # Step 1: Check data
    benjamin_user, merban_affiliate = check_ceo_affiliate_data()
    
    # Step 2: Fix if needed
    if benjamin_user:
        fix_benjamin_affiliate(benjamin_user, merban_affiliate)
        # Reload user after fix
        benjamin_user = User.objects.get(id=benjamin_user.id)
    
    # Step 3-5: Check filtering logic
    check_approval_queue_filtering()
    check_leave_request_viewset_logic()
    check_ceo_approval_routing()
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")

if __name__ == "__main__":
    main()