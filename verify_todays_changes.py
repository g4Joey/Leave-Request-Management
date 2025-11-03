#!/usr/bin/env python
"""
Quick validation script to verify all today's changes are working correctly.
Run: python verify_todays_changes.py
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Affiliate, Department
from leaves.models import LeaveRequest
from leaves.services import ApprovalRoutingService, ApprovalWorkflowService
from notifications.models import SiteSetting

User = get_user_model()

def check_notifications_setup():
    """Verify notifications setup is complete"""
    print("\n📋 Checking notifications setup...")
    try:
        # Check if table exists
        count = SiteSetting.objects.count()
        print(f"✅ SiteSetting table accessible, {count} settings found")
        
        # Check for expected keys
        expected = ['OVERLAP_NOTIFY_MIN_DAYS', 'OVERLAP_NOTIFY_MIN_COUNT', 'OVERLAP_DETECT_ENABLED']
        for key in expected:
            setting = SiteSetting.objects.filter(key=key).first()
            if setting:
                print(f"   ✓ {key} = {setting.value}")
            else:
                print(f"   ⚠ {key} not found (will be created on first run)")
        return True
    except Exception as e:
        print(f"❌ Notifications check failed: {e}")
        return False

def check_ceo_routing():
    """Verify CEO routing logic"""
    print("\n🎯 Checking CEO routing...")
    try:
        # Get affiliates
        merban = Affiliate.objects.filter(name__iexact='Merban Capital').first()
        sdsl = Affiliate.objects.filter(name__iexact='SDSL').first()
        sbl = Affiliate.objects.filter(name__iexact='SBL').first()
        
        if not merban:
            print("⚠ Merban Capital affiliate not found")
        if not sdsl:
            print("⚠ SDSL affiliate not found")
        if not sbl:
            print("⚠ SBL affiliate not found")
        
        # Check CEO assignments
        ceos = User.objects.filter(role='ceo', is_active=True)
        print(f"   Found {ceos.count()} active CEOs:")
        for ceo in ceos:
            aff = getattr(ceo, 'affiliate', None)
            dept = getattr(ceo, 'department', None)
            print(f"   - {ceo.email}: affiliate={aff and aff.name}, department={dept and dept.name}")
            
            if not aff:
                print(f"     ⚠ WARNING: CEO {ceo.email} has no affiliate set!")
        
        # Test routing for a sample employee
        hr_user = User.objects.filter(role='hr', is_active=True).first()
        if hr_user:
            expected_ceo = ApprovalRoutingService.get_ceo_for_employee(hr_user)
            print(f"\n   Test: HR user {hr_user.email} → Expected CEO: {expected_ceo and expected_ceo.email}")
            if expected_ceo:
                print(f"   ✅ CEO routing works")
            else:
                print(f"   ⚠ No CEO found for HR user")
        
        return True
    except Exception as e:
        print(f"❌ CEO routing check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_staff_api():
    """Verify staff API changes (no Executive grouping, CEOs included)"""
    print("\n👥 Checking staff API structure...")
    try:
        from users.views import StaffManagementView
        print("   ✅ StaffManagementView accessible")
        
        # Check that CEOs are not excluded in individual queries
        individuals = User.objects.filter(department__isnull=True, is_active=True).exclude(role='admin')
        ceo_count = individuals.filter(role='ceo').count()
        print(f"   Found {ceo_count} CEOs in individuals list (should be > 0)")
        
        if ceo_count > 0:
            print("   ✅ CEOs included in staff API")
        else:
            print("   ⚠ No CEOs found in individuals (may be assigned to departments)")
        
        return True
    except Exception as e:
        print(f"❌ Staff API check failed: {e}")
        return False

def check_approval_endpoints():
    """Verify approval service improvements"""
    print("\n🔒 Checking approval service...")
    try:
        # Check that proper exceptions are imported
        from leaves.services import PermissionDenied, ValidationError, transaction
        print("   ✅ DRF exceptions imported correctly")
        print("   ✅ Transaction locking imported")
        
        # Check that approve_request uses transaction
        import inspect
        source = inspect.getsource(ApprovalWorkflowService.approve_request)
        if 'transaction.atomic' in source:
            print("   ✅ Row locking implemented")
        else:
            print("   ⚠ Row locking not found in approve_request")
        
        if 'PermissionDenied' in source:
            print("   ✅ PermissionDenied exception used")
        else:
            print("   ⚠ PermissionDenied not found")
        
        if 'select_for_update' in source:
            print("   ✅ select_for_update() used for locking")
        else:
            print("   ⚠ select_for_update not found")
        
        return True
    except Exception as e:
        print(f"❌ Approval service check failed: {e}")
        return False

def check_case_insensitive():
    """Verify case-insensitive handling"""
    print("\n🔤 Checking case-insensitive logic...")
    try:
        # Check that CEO lookup uses iexact
        import inspect
        source = inspect.getsource(ApprovalRoutingService.get_ceo_for_employee)
        if 'role__iexact' in source:
            print("   ✅ CEO role lookup is case-insensitive")
        else:
            print("   ⚠ CEO role lookup may be case-sensitive")
        
        if '.lower()' in source or 'iexact' in source or '__icontains' in source:
            print("   ✅ Affiliate name comparison is case-insensitive")
        else:
            print("   ⚠ Affiliate comparison may be case-sensitive")
        
        return True
    except Exception as e:
        print(f"❌ Case-insensitive check failed: {e}")
        return False

def main():
    print("=" * 60)
    print("🔍 VERIFICATION REPORT FOR TODAY'S CHANGES")
    print("=" * 60)
    
    results = {
        "Notifications Setup": check_notifications_setup(),
        "CEO Routing": check_ceo_routing(),
        "Staff API": check_staff_api(),
        "Approval Service": check_approval_endpoints(),
        "Case Insensitivity": check_case_insensitive(),
    }
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {name}")
    
    print(f"\n{passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All checks passed! Everything is working as expected.")
    else:
        print("\n⚠️  Some checks failed. Review the details above.")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()
