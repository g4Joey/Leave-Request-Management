#!/usr/bin/env python
"""
Production User Reset Script
============================
Deletes all user data for production refresh while preserving system structure.

What this script does:
- Deletes ALL users (employees, managers, HR) except superusers
- Deletes ALL leave requests and balances
- Preserves departments, affiliates, leave types, and system configuration
- Resets the system to allow fresh CSV imports or seeding

Use this for production data refresh when you need a clean slate.

Environment Variable Trigger:
- Set RUN_RESET_PRODUCTION_USERS=1 in your deployment environment variables
- The reset will run automatically on startup
- Remember to set it back to 0 after deployment completes
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.db import transaction
from django.contrib.auth import get_user_model
from leaves.models import LeaveRequest, LeaveBalance
from django.utils import timezone

User = get_user_model()


def reset_production_users(confirm_text: str = None, auto_confirm: bool = False):
    """
    Reset all user data for production refresh.
    
    Args:
        confirm_text: Must be "RESET PRODUCTION USERS" to proceed (if not auto_confirm)
        auto_confirm: If True, skip confirmation (used for env var trigger)
    """
    if not auto_confirm and confirm_text != "RESET PRODUCTION USERS":
        print("❌ Invalid confirmation. Script aborted.")
        print("   To proceed, run: python reset_production_users.py")
        print('   And type: RESET PRODUCTION USERS')
        return False
    
    print("\n" + "="*60)
    print("🔄 PRODUCTION USER RESET - Starting...")
    if auto_confirm:
        print("   (Triggered by RUN_RESET_PRODUCTION_USERS environment variable)")
    print("="*60 + "\n")
    
    try:
        with transaction.atomic():
            # Count before deletion
            all_users = User.objects.count()
            superusers = User.objects.filter(is_superuser=True).count()
            regular_users = User.objects.filter(is_superuser=False).count()
            requests_count = LeaveRequest.objects.count()
            balances_count = LeaveBalance.objects.count()
            
            print(f"📊 Current Statistics:")
            print(f"   - Total Users: {all_users}")
            print(f"   - Superusers (preserved): {superusers}")
            print(f"   - Regular Users (to delete): {regular_users}")
            print(f"   - Leave Requests: {requests_count}")
            print(f"   - Leave Balances: {balances_count}\n")
            
            # Delete all leave requests first (foreign key constraints)
            print("🗑️  Deleting all leave requests...")
            LeaveRequest.objects.all().delete()
            print(f"   ✓ Deleted {requests_count} leave request(s)")
            
            # Delete all leave balances
            print("🗑️  Deleting all leave balances...")
            LeaveBalance.objects.all().delete()
            print(f"   ✓ Deleted {balances_count} leave balance(s)")
            
            # Delete all non-superuser accounts
            print("🗑️  Deleting all regular user accounts...")
            deleted_users = User.objects.filter(is_superuser=False).delete()
            actual_deleted = deleted_users[0] if deleted_users else 0
            print(f"   ✓ Deleted {actual_deleted} regular user account(s)")
            print(f"   ✓ Preserved {superusers} superuser account(s)\n")
            
            # Write a marker file
            try:
                marker_dir = '/tmp'
                marker_path = os.path.join(marker_dir, f'production_reset_run_{int(timezone.now().timestamp())}.txt')
                with open(marker_path, 'w') as mf:
                    mf.write(f"production_reset_run_at={timezone.now().isoformat()}\n")
                    mf.write(f"deleted_users={actual_deleted}\n")
                    mf.write(f"deleted_requests={requests_count}\n")
                    mf.write(f"deleted_balances={balances_count}\n")
                    mf.write(f"preserved_superusers={superusers}\n")
                print(f"   ✓ Wrote marker file: {marker_path}\n")
            except Exception:
                print("   ⚠️  Failed to write marker file (non-fatal)")
            
            # Summary
            print("="*60)
            print("✅ PRODUCTION USER RESET COMPLETED SUCCESSFULLY")
            print("="*60)
            print(f"\nSummary:")
            print(f"  • Deleted {actual_deleted} regular user accounts")
            print(f"  • Deleted {requests_count} leave requests")
            print(f"  • Deleted {balances_count} leave balances")
            print(f"  • Preserved {superusers} superuser accounts")
            print(f"  • All departments preserved")
            print(f"  • All affiliates preserved")
            print(f"  • All leave types preserved\n")
            
            print("🎯 System is now ready for fresh user imports via CSV or seeding!\n")
            
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR during reset: {str(e)}")
        print("   Transaction rolled back - no changes applied.\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    # Check for environment variable trigger
    env_trigger = os.environ.get('RUN_RESET_PRODUCTION_USERS', '0').strip()
    
    if env_trigger == '1':
        print("\n" + "🔔 "*20)
        print("ENVIRONMENT VARIABLE TRIGGER DETECTED")
        print("🔔 "*20)
        print("\nRUN_RESET_PRODUCTION_USERS=1 detected")
        print("Proceeding with automatic production user reset...\n")
        success = reset_production_users(auto_confirm=True)
        if success:
            print("\n⚠️  IMPORTANT: Set RUN_RESET_PRODUCTION_USERS=0 to prevent future resets!\n")
        sys.exit(0 if success else 1)
    
    # Interactive mode
    print("\n" + "⚠️ "*25)
    print("WARNING: PRODUCTION USER DATA RESET")
    print("⚠️ "*25)
    print("\nThis script will:")
    print("  1. DELETE ALL regular user accounts (cannot be undone)")
    print("  2. DELETE ALL leave requests and balances")
    print("  3. PRESERVE superuser accounts and system structure")
    print("  4. ALLOW fresh CSV imports or user seeding")
    print("\nThis is for production data refresh only!")
    print("\n" + "-"*60 + "\n")
    
    confirmation = input('Type "RESET PRODUCTION USERS" to proceed (or anything else to cancel): ')
    
    if confirmation.strip() == "RESET PRODUCTION USERS":
        success = reset_production_users(confirmation.strip())
        sys.exit(0 if success else 1)
    else:
        print("\n❌ Reset cancelled. No changes made.\n")
        sys.exit(0)