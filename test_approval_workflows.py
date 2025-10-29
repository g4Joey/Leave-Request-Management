#!/usr/bin/env python
"""
Test leave approval workflows to ensure 3-tier MERBAN vs 2-tier SDSL/SBL flows work correctly.
"""

import os
import django
import sys
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser, Department, Affiliate
from leaves.models import LeaveRequest, LeaveType
from leaves.services import ApprovalRoutingService, StandardApprovalHandler, SDSLApprovalHandler

def test_approval_workflows():
    """Test the different approval workflows for MERBAN vs SDSL/SBL."""
    
    print("=== LEAVE APPROVAL WORKFLOW TESTING ===\n")
    
    # Get test data
    try:
        merban_affiliate = Affiliate.objects.get(name__iexact='MERBAN CAPITAL')
        sdsl_affiliate = Affiliate.objects.get(name__iexact='SDSL')
        sbl_affiliate = Affiliate.objects.get(name__iexact='SBL')
    except Affiliate.DoesNotExist as e:
        print(f"❌ Required affiliate not found: {e}")
        return False
    
    # Get CEOs
    try:
        benjamin_ceo = CustomUser.objects.get(email='ceo@umbcapital.com', role='ceo')
        kofi_ceo = CustomUser.objects.get(email='sdslceo@umbcapital.com', role='ceo')  
        winslow_ceo = CustomUser.objects.get(email='sblceo@umbcapital.com', role='ceo')
        print(f"✅ CEOs found:")
        print(f"   Merban: {benjamin_ceo.get_full_name()}")
        print(f"   SDSL: {kofi_ceo.get_full_name()}")
        print(f"   SBL: {winslow_ceo.get_full_name()}")
    except CustomUser.DoesNotExist as e:
        print(f"❌ Required CEO not found: {e}")
        return False
    
    # Get HR user
    try:
        hr_user = CustomUser.objects.filter(role='hr', is_active=True).first()
        if not hr_user:
            print("❌ No HR user found")
            return False
        print(f"✅ HR user: {hr_user.get_full_name()}")
    except Exception as e:
        print(f"❌ Error getting HR user: {e}")
        return False
    
    # Get leave type
    try:
        annual_leave = LeaveType.objects.filter(name__icontains='Annual').first()
        if not annual_leave:
            print("❌ No Annual leave type found")
            return False
        print(f"✅ Leave type: {annual_leave.name}")
    except Exception as e:
        print(f"❌ Error getting leave type: {e}")
        return False
    
    print("\n" + "="*60)
    
    # Test 1: MERBAN 3-tier workflow (staff → HOD → HR → CEO)
    print("\n🧪 TEST 1: MERBAN 3-Tier Approval Workflow")
    print("Expected: staff → HOD → HR → CEO (Benjamin Ackah)")
    
    # Find a Merban department with staff
    merban_dept = Department.objects.filter(affiliate=merban_affiliate).exclude(
        name__iexact='executive'
    ).first()
    
    if merban_dept:
        print(f"✅ Using Merban department: {merban_dept.name}")
        
        # Create a mock employee for testing workflow logic
        class MockMerbanEmployee:
            def __init__(self):
                self.department = merban_dept
                self.role = 'junior_staff'
                self.manager = merban_dept.hod if hasattr(merban_dept, 'hod') and merban_dept.hod else None
        
        mock_emp = MockMerbanEmployee()
        
        # Test routing service
        expected_ceo = ApprovalRoutingService.get_ceo_for_employee(mock_emp)
        if expected_ceo == benjamin_ceo:
            print(f"✅ CEO routing correct: {expected_ceo.get_full_name()}")
        else:
            print(f"❌ CEO routing incorrect: got {expected_ceo.get_full_name() if expected_ceo else None}, expected {benjamin_ceo.get_full_name()}")
        
        # Test approval handler
        class MockLeaveRequest:
            def __init__(self, employee):
                self.employee = employee
        
        mock_request = MockLeaveRequest(mock_emp)
        handler = StandardApprovalHandler(mock_request)
        
        # Test flow steps
        flow = handler.get_approval_flow()
        print(f"✅ Merban workflow: {flow}")
        
        # Verify 3-tier flow
        expected_flow = {
            'pending': 'manager',
            'manager_approved': 'hr', 
            'hr_approved': 'ceo'
        }
        if flow == expected_flow:
            print("✅ 3-tier flow structure correct")
        else:
            print(f"❌ 3-tier flow incorrect: got {flow}, expected {expected_flow}")
    else:
        print("❌ No Merban department found for testing")
    
    print("\n" + "="*60)
    
    # Test 2: SDSL 2-tier workflow (staff → CEO → HR)  
    print("\n🧪 TEST 2: SDSL 2-Tier Approval Workflow")
    print("Expected: staff → CEO (Kofi Ameyaw) → HR")
    
    # Find SDSL department 
    sdsl_dept = Department.objects.filter(affiliate=sdsl_affiliate).first()
    
    if sdsl_dept:
        print(f"✅ Using SDSL department: {sdsl_dept.name}")
        
        class MockSDSLEmployee:
            def __init__(self):
                self.department = sdsl_dept
                self.role = 'junior_staff'
                self.manager = None  # SDSL may not have traditional managers
        
        mock_sdsl_emp = MockSDSLEmployee()
        
        # Test CEO routing
        expected_ceo = ApprovalRoutingService.get_ceo_for_employee(mock_sdsl_emp)
        if expected_ceo == kofi_ceo:
            print(f"✅ SDSL CEO routing correct: {expected_ceo.get_full_name()}")
        else:
            print(f"❌ SDSL CEO routing incorrect: got {expected_ceo.get_full_name() if expected_ceo else None}, expected {kofi_ceo.get_full_name()}")
        
        # Test SDSL handler
        mock_sdsl_request = MockLeaveRequest(mock_sdsl_emp)
        sdsl_handler = SDSLApprovalHandler(mock_sdsl_request)
        
        sdsl_flow = sdsl_handler.get_approval_flow()
        print(f"✅ SDSL workflow: {sdsl_flow}")
        
        # Verify 2-tier flow structure
        expected_sdsl_flow = {
            'pending': 'manager',
            'manager_approved': 'ceo',
            'hr_approved': 'hr'
        }
        if sdsl_flow == expected_sdsl_flow:
            print("✅ SDSL 2-tier flow structure correct")
        else:
            print(f"❌ SDSL flow incorrect: got {sdsl_flow}, expected {expected_sdsl_flow}")
    else:
        print("❌ No SDSL department found for testing")
    
    print("\n" + "="*60)
    
    # Test 3: SBL workflow (should use 2-tier like SDSL)
    print("\n🧪 TEST 3: SBL 2-Tier Approval Workflow")
    print("Expected: staff → CEO (Winslow Sackey) → HR")
    
    sbl_dept = Department.objects.filter(affiliate=sbl_affiliate).first() 
    
    if sbl_dept:
        print(f"✅ Using SBL department: {sbl_dept.name}")
        
        class MockSBLEmployee:
            def __init__(self):
                self.department = sbl_dept
                self.role = 'junior_staff'
                self.manager = None
        
        mock_sbl_emp = MockSBLEmployee()
        
        # Test CEO routing
        expected_ceo = ApprovalRoutingService.get_ceo_for_employee(mock_sbl_emp)
        if expected_ceo == winslow_ceo:
            print(f"✅ SBL CEO routing correct: {expected_ceo.get_full_name()}")
        else:
            print(f"❌ SBL CEO routing incorrect: got {expected_ceo.get_full_name() if expected_ceo else None}, expected {winslow_ceo.get_full_name()}")
        
        # SBL should use SBLApprovalHandler (2-tier workflow)
        from leaves.services import SBLApprovalHandler
        mock_sbl_request = MockLeaveRequest(mock_sbl_emp)
        sbl_handler = SBLApprovalHandler(mock_sbl_request)
        
        sbl_flow = sbl_handler.get_approval_flow()
        print(f"✅ SBL workflow: {sbl_flow}")
        
        # Should match 2-tier SBL flow
        expected_sbl_flow = {
            'pending': 'manager',
            'manager_approved': 'ceo',
            'hr_approved': 'hr'
        }
        if sbl_flow == expected_sbl_flow:
            print("✅ SBL 2-tier flow structure correct")
        else:
            print(f"❌ SBL flow incorrect: got {sbl_flow}, expected {expected_sbl_flow}")
    else:
        print("❌ No SBL department found for testing")
    
    print("\n" + "="*60)
    print("\n✅ WORKFLOW TESTING COMPLETE")
    print("\n📋 SUMMARY:")
    print("• MERBAN CAPITAL: 3-tier (staff → HOD → HR → CEO Benjamin)")
    print("• SDSL: 2-tier (staff → CEO Kofi → HR)")  
    print("• SBL: 2-tier (staff → CEO Winslow → HR)")
    
    return True

if __name__ == "__main__":
    try:
        test_approval_workflows()
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)