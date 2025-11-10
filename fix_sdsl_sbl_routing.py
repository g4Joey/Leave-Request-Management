#!/usr/bin/env python
"""
Fix SDSL/SBL staff routing by ensuring data integrity.

This script:
1. Ensures all SDSL staff have affiliate='SDSL' and no department/manager
2. Ensures all SBL staff have affiliate='SBL' and no department/manager
3. Ensures all CEOs have their correct affiliate set
4. Verifies Merban staff have proper setup

Usage:
    python fix_sdsl_sbl_routing.py [--dry-run]
    
Options:
    --dry-run    Show what would be changed without actually changing it
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Affiliate
from django.db import transaction

User = get_user_model()


def fix_affiliate_staff(affiliate_name, dry_run=False):
    """Fix staff for a specific affiliate"""
    print(f"\n{'=' * 80}")
    print(f"Fixing {affiliate_name} Staff")
    print(f"{'=' * 80}\n")
    
    try:
        affiliate = Affiliate.objects.get(name__iexact=affiliate_name)
    except Affiliate.DoesNotExist:
        print(f"❌ Affiliate '{affiliate_name}' not found. Creating it...")
        if not dry_run:
            affiliate = Affiliate.objects.create(name=affiliate_name)
            print(f"✅ Created affiliate: {affiliate_name}")
        else:
            print(f"   [DRY RUN] Would create affiliate: {affiliate_name}")
            return
    
    # Find staff by affiliate or by email pattern
    staff_by_affiliate = User.objects.filter(
        affiliate=affiliate,
        is_active=True
    ).exclude(role__in=['admin'])
    
    # Also find by email pattern (e.g., @sdsl.com, @sbl.com)
    if affiliate_name.upper() == 'SDSL':
        email_pattern = '@sdsl'
    elif affiliate_name.upper() == 'SBL':
        email_pattern = '@sbl'
    else:
        email_pattern = None
    
    if email_pattern:
        staff_by_email = User.objects.filter(
            email__icontains=email_pattern,
            is_active=True
        ).exclude(role__in=['admin'])
    else:
        staff_by_email = User.objects.none()
    
    # Combine both querysets
    all_staff = (staff_by_affiliate | staff_by_email).distinct()
    
    if not all_staff.exists():
        print(f"⚠️  No staff found for {affiliate_name}")
        return
    
    print(f"Found {all_staff.count()} staff members for {affiliate_name}:\n")
    
    changes_made = 0
    
    for user in all_staff:
        print(f"👤 {user.email} (Role: {user.role})")
        user_changed = False
        
        # Check affiliate
        if user.affiliate != affiliate:
            print(f"   ⚠️  Affiliate: {user.affiliate.name if user.affiliate else 'NOT SET'} → {affiliate_name}")
            if not dry_run:
                user.affiliate = affiliate
                user_changed = True
            else:
                print(f"      [DRY RUN] Would set affiliate to {affiliate_name}")
        else:
            print(f"   ✅ Affiliate: {affiliate_name}")
        
        # For SDSL/SBL: ensure no department or manager
        if affiliate_name.upper() in ['SDSL', 'SBL']:
            if user.department is not None:
                dept_name = user.department.name
                print(f"   ⚠️  Department: {dept_name} → None (SDSL/SBL should have no department)")
                if not dry_run:
                    user.department = None
                    user_changed = True
                else:
                    print(f"      [DRY RUN] Would clear department")
            else:
                print(f"   ✅ Department: None (correct for {affiliate_name})")
            
            if user.manager is not None:
                mgr_email = user.manager.email
                print(f"   ⚠️  Manager: {mgr_email} → None (SDSL/SBL should have no manager)")
                if not dry_run:
                    user.manager = None
                    user_changed = True
                else:
                    print(f"      [DRY RUN] Would clear manager")
            else:
                print(f"   ✅ Manager: None (correct for {affiliate_name})")
        
        # For Merban: ensure they have a department (except CEOs)
        elif affiliate_name.upper() in ['MERBAN', 'MERBAN CAPITAL']:
            if user.role not in ['ceo', 'admin']:
                if user.department is None:
                    print(f"   ⚠️  Department: None (Merban non-CEO staff should have a department)")
                    print(f"      ℹ️  Skipping - requires manual assignment")
                else:
                    print(f"   ✅ Department: {user.department.name}")
        
        if user_changed:
            if not dry_run:
                user.save()
                changes_made += 1
                print(f"   ✅ Updated user")
        
        print()
    
    if dry_run:
        print(f"[DRY RUN] Would have updated {changes_made} users")
    else:
        print(f"✅ Updated {changes_made} users for {affiliate_name}")


def fix_ceos(dry_run=False):
    """Ensure all CEOs have correct affiliate"""
    print(f"\n{'=' * 80}")
    print("Fixing CEO Affiliates")
    print(f"{'=' * 80}\n")
    
    ceos = User.objects.filter(role='ceo', is_active=True)
    
    if not ceos.exists():
        print("⚠️  No CEOs found!")
        return
    
    print(f"Found {ceos.count()} CEOs:\n")
    
    changes_made = 0
    
    for ceo in ceos:
        print(f"👔 {ceo.email}")
        ceo_changed = False
        
        # Try to determine affiliate from email
        email_lower = ceo.email.lower()
        expected_affiliate = None
        
        if 'sdsl' in email_lower:
            expected_affiliate = 'SDSL'
        elif 'sbl' in email_lower:
            expected_affiliate = 'SBL'
        elif 'merban' in email_lower or 'umb' in email_lower:
            expected_affiliate = 'MERBAN CAPITAL'
        
        if expected_affiliate:
            try:
                affiliate = Affiliate.objects.get(name__iexact=expected_affiliate)
                if ceo.affiliate != affiliate:
                    print(f"   ⚠️  Affiliate: {ceo.affiliate.name if ceo.affiliate else 'NOT SET'} → {affiliate.name}")
                    if not dry_run:
                        ceo.affiliate = affiliate
                        ceo_changed = True
                    else:
                        print(f"      [DRY RUN] Would set affiliate to {affiliate.name}")
                else:
                    print(f"   ✅ Affiliate: {affiliate.name}")
            except Affiliate.DoesNotExist:
                print(f"   ⚠️  Expected affiliate '{expected_affiliate}' not found - needs to be created first")
        else:
            print(f"   ⚠️  Cannot determine affiliate from email - manual intervention needed")
            print(f"      Current affiliate: {ceo.affiliate.name if ceo.affiliate else 'NOT SET'}")
        
        # CEOs should not have department (optional check)
        if ceo.department is not None:
            print(f"   ℹ️  Department: {ceo.department.name} (CEOs typically don't need departments)")
        
        if ceo_changed:
            if not dry_run:
                ceo.save()
                changes_made += 1
                print(f"   ✅ Updated CEO")
        
        print()
    
    if dry_run:
        print(f"[DRY RUN] Would have updated {changes_made} CEOs")
    else:
        print(f"✅ Updated {changes_made} CEOs")


def main():
    dry_run = '--dry-run' in sys.argv
    
    if dry_run:
        print("\n" + "=" * 80)
        print("🔍 DRY RUN MODE - No changes will be made")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("⚠️  LIVE MODE - Changes will be saved to database")
        print("=" * 80)
        print("\nPress Ctrl+C to cancel, or Enter to continue...")
        try:
            input()
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            return
    
    with transaction.atomic():
        # Fix CEOs first
        fix_ceos(dry_run)
        
        # Fix each affiliate
        fix_affiliate_staff('SDSL', dry_run)
        fix_affiliate_staff('SBL', dry_run)
        fix_affiliate_staff('MERBAN CAPITAL', dry_run)
        
        if dry_run:
            print("\n" + "=" * 80)
            print("✅ Dry run complete - no changes made")
            print("=" * 80)
            print("\nRun without --dry-run to apply these changes")
        else:
            print("\n" + "=" * 80)
            print("✅ All fixes applied successfully!")
            print("=" * 80)
            print("\nRun diagnose_ceo_routing.py to verify the fixes")


if __name__ == '__main__':
    main()
