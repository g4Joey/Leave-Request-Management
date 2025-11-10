#!/usr/bin/env python
"""
Diagnostic script to verify CEO routing for SDSL/SBL staff.

Usage:
    python diagnose_ceo_routing.py
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Affiliate, Department
from leaves.services import ApprovalRoutingService

User = get_user_model()


def diagnose_staff_routing():
    """Check each staff member's CEO routing"""
    print("=" * 80)
    print("CEO ROUTING DIAGNOSTIC")
    print("=" * 80)
    print()
    
    # Get all affiliates
    affiliates = Affiliate.objects.all()
    print(f"📊 Found {affiliates.count()} Affiliates:")
    for aff in affiliates:
        print(f"  - {aff.name}")
    print()
    
    # Get all CEOs
    ceos = User.objects.filter(role='ceo', is_active=True)
    print(f"👔 Found {ceos.count()} CEOs:")
    for ceo in ceos:
        aff_name = getattr(ceo.affiliate, 'name', 'NO AFFILIATE') if ceo.affiliate else 'NO AFFILIATE'
        dept_name = getattr(ceo.department, 'name', 'None') if ceo.department else 'None'
        print(f"  - {ceo.email:30s} | Affiliate: {aff_name:20s} | Department: {dept_name}")
    print()
    
    # Check each affiliate's staff
    for affiliate in affiliates:
        print(f"\n{'=' * 80}")
        print(f"🏢 AFFILIATE: {affiliate.name}")
        print(f"{'=' * 80}")
        
        # Find staff for this affiliate
        staff_users = User.objects.filter(
            affiliate=affiliate,
            is_active=True
        ).exclude(
            role__in=['ceo', 'admin']
        ).order_by('role', 'email')
        
        if not staff_users.exists():
            print("  ⚠️  No staff found for this affiliate")
            continue
        
        print(f"\n  Found {staff_users.count()} staff members:")
        print()
        
        for user in staff_users:
            print(f"  👤 {user.email:30s} (Role: {user.role})")
            print(f"     User Affiliate:       {user.affiliate.name if user.affiliate else 'NOT SET'}")
            print(f"     Department:           {user.department.name if user.department else 'NOT SET'}")
            
            if user.department and user.department.affiliate:
                print(f"     Department Affiliate: {user.department.affiliate.name}")
            else:
                print(f"     Department Affiliate: N/A")
            
            # Test routing
            try:
                affiliate_name = ApprovalRoutingService.get_employee_affiliate_name(user)
                ceo = ApprovalRoutingService.get_ceo_for_employee(user)
                
                print(f"     ➡️  Resolved Affiliate:  {affiliate_name if affiliate_name else '❌ NONE'}")
                
                if ceo:
                    ceo_aff = getattr(ceo.affiliate, 'name', 'unknown') if ceo.affiliate else 'unknown'
                    print(f"     ✅ Routed to CEO:      {ceo.email} (Affiliate: {ceo_aff})")
                    
                    # Verify correct CEO
                    expected_aff = affiliate.name.upper()
                    resolved_aff = affiliate_name.upper()
                    ceo_aff_upper = ceo_aff.upper()
                    
                    # Handle Merban synonyms
                    if expected_aff in ['MERBAN', 'MERBAN CAPITAL']:
                        is_correct = ceo_aff_upper in ['MERBAN', 'MERBAN CAPITAL']
                    else:
                        is_correct = ceo_aff_upper == expected_aff
                    
                    if is_correct:
                        print(f"     ✅ CORRECT CEO")
                    else:
                        print(f"     ❌ WRONG CEO! Expected {expected_aff} CEO, got {ceo_aff_upper} CEO")
                else:
                    print(f"     ❌ No CEO found - REQUEST WILL BE INVISIBLE!")
            except Exception as e:
                print(f"     ❌ ERROR: {e}")
            
            print()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    # Count issues
    issues = []
    for affiliate in affiliates:
        staff_users = User.objects.filter(
            affiliate=affiliate,
            is_active=True
        ).exclude(role__in=['ceo', 'admin'])
        
        for user in staff_users:
            ceo = ApprovalRoutingService.get_ceo_for_employee(user)
            if not ceo:
                issues.append(f"❌ {user.email}: No CEO found")
            else:
                expected_aff = affiliate.name.upper()
                ceo_aff = getattr(ceo.affiliate, 'name', '').upper()
                
                # Handle Merban synonyms
                if expected_aff in ['MERBAN', 'MERBAN CAPITAL']:
                    is_correct = ceo_aff in ['MERBAN', 'MERBAN CAPITAL']
                else:
                    is_correct = ceo_aff == expected_aff
                
                if not is_correct:
                    issues.append(f"❌ {user.email}: Wrong CEO (expected {expected_aff}, got {ceo_aff})")
    
    if issues:
        print(f"\n⚠️  Found {len(issues)} issues:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n✅ All staff members are correctly routed to their affiliate's CEO!")
    
    print()


def suggest_fixes():
    """Suggest data fixes if issues are found"""
    print("\n" + "=" * 80)
    print("DATA INTEGRITY CHECKS & SUGGESTED FIXES")
    print("=" * 80)
    print()
    
    # Check for SDSL/SBL staff with departments
    sdsl_sbl_with_dept = User.objects.filter(
        affiliate__name__in=['SDSL', 'SBL'],
        department__isnull=False,
        is_active=True
    ).exclude(role__in=['ceo', 'admin'])
    
    if sdsl_sbl_with_dept.exists():
        print("⚠️  SDSL/SBL staff should NOT have departments:")
        for user in sdsl_sbl_with_dept:
            print(f"  - {user.email}: Currently in {user.department.name}")
        print("\n  Fix with:")
        print("    from django.contrib.auth import get_user_model")
        print("    User = get_user_model()")
        print("    User.objects.filter(affiliate__name__in=['SDSL', 'SBL']).update(department=None, manager=None)")
        print()
    
    # Check for staff without affiliate
    staff_no_affiliate = User.objects.filter(
        affiliate__isnull=True,
        is_active=True
    ).exclude(role__in=['admin']).exclude(is_superuser=True)
    
    if staff_no_affiliate.exists():
        print("⚠️  Staff without affiliate (will not route to any CEO):")
        for user in staff_no_affiliate:
            dept = user.department.name if user.department else "No department"
            print(f"  - {user.email}: {dept}")
        print("\n  Fix by setting user.affiliate for each user")
        print()
    
    # Check for CEOs without affiliate
    ceos_no_affiliate = User.objects.filter(
        role='ceo',
        affiliate__isnull=True,
        is_active=True
    )
    
    if ceos_no_affiliate.exists():
        print("⚠️  CEOs without affiliate:")
        for ceo in ceos_no_affiliate:
            print(f"  - {ceo.email}")
        print("\n  Fix by setting ceo.affiliate to their respective affiliate")
        print()
    
    # Check for CEOs with departments (not recommended)
    ceos_with_dept = User.objects.filter(
        role='ceo',
        department__isnull=False,
        is_active=True
    )
    
    if ceos_with_dept.exists():
        print("ℹ️  CEOs with departments (not needed, but won't cause issues):")
        for ceo in ceos_with_dept:
            print(f"  - {ceo.email}: {ceo.department.name}")
        print()


if __name__ == '__main__':
    diagnose_staff_routing()
    suggest_fixes()
