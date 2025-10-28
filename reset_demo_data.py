#!/usr/bin/env python
"""
Demo Data Reset Script
======================
Resets leave requests and balances for demo purposes while preserving user accounts.

What this script does:
- Deletes ALL leave requests (history cleared)
- Resets all leave balances: sets used_days=0, pending_days=0
- Preserves entitled_days and all user accounts
- Preserves departments, affiliates, and leave types

Use this before CEO demo to show clean slate with realistic users.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.db import transaction
from leaves.models import LeaveRequest, LeaveBalance
from django.utils import timezone


def reset_demo_data(confirm_text: str = None):
    """
    Reset leave data for demo purposes.
    
    Args:
        confirm_text: Must be "RESET DEMO DATA" to proceed
    """
    if confirm_text != "RESET DEMO DATA":
        print("❌ Invalid confirmation. Script aborted.")
        print("   To proceed, run: python reset_demo_data.py")
        print('   And type: RESET DEMO DATA')
        return False
    
    print("\n" + "="*60)
    print("🔄 DEMO DATA RESET - Starting...")
    print("="*60 + "\n")
    
    try:
        with transaction.atomic():
            # Count before deletion
            requests_count = LeaveRequest.objects.count()
            balances_count = LeaveBalance.objects.filter(
                used_days__gt=0
            ).count() + LeaveBalance.objects.filter(pending_days__gt=0).count()
            
            current_year = timezone.now().year
            
            print(f"📊 Current Statistics:")
            print(f"   - Leave Requests: {requests_count}")
            print(f"   - Balances with usage: {balances_count}")
            print(f"   - Current Year: {current_year}\n")
            
            # Delete all leave requests
            print("🗑️  Deleting all leave requests...")
            LeaveRequest.objects.all().delete()
            print(f"   ✓ Deleted {requests_count} leave request(s)\n")
            
            # Reset all balances (current year only)
            print("♻️  Resetting leave balances for current year...")
            updated = LeaveBalance.objects.filter(year=current_year).update(
                used_days=0,
                pending_days=0
            )
            print(f"   ✓ Reset {updated} balance record(s)\n")
            
            # Summary
            print("="*60)
            print("✅ DEMO DATA RESET COMPLETED SUCCESSFULLY")
            print("="*60)
            print(f"\nSummary:")
            print(f"  • Deleted {requests_count} leave requests")
            print(f"  • Reset {updated} leave balances (year {current_year})")
            print(f"  • All users preserved")
            print(f"  • All departments preserved")
            print(f"  • All leave types preserved")
            print(f"  • Entitled days preserved\n")
            
            print("🎯 System is now ready for CEO demo!\n")
            
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR during reset: {str(e)}")
        print("   Transaction rolled back - no changes applied.\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n" + "⚠️ "*20)
    print("WARNING: DEMO DATA RESET")
    print("⚠️ "*20)
    print("\nThis script will:")
    print("  1. DELETE all leave requests (cannot be undone)")
    print("  2. RESET all leave balances to zero")
    print("  3. PRESERVE all user accounts and entitlements")
    print("\nThis is intended for demo preparation only!")
    print("\n" + "-"*60 + "\n")
    
    confirmation = input('Type "RESET DEMO DATA" to proceed (or anything else to cancel): ')
    
    if confirmation.strip() == "RESET DEMO DATA":
        success = reset_demo_data(confirmation.strip())
        sys.exit(0 if success else 1)
    else:
        print("\n❌ Reset cancelled. No changes made.\n")
        sys.exit(0)
