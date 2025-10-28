#!/usr/bin/env python
"""
Complete Database Cleanup Script
================================
Aggressively wipes ALL user data and personal information from the database.
Keeps only the application structure (departments, affiliates, leave types, system config).

What this script does:
- Deletes ALL users (including staff, managers, HR, CEOs) except superusers
- Deletes ALL leave requests, balances, and related personal data
- Deletes ALL notifications and user-related records  
- Preserves departments, affiliates, leave types, policies, grades
- Resets the database to a clean structural state

This is for complete production data wipe - more aggressive than other reset scripts.
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
from leaves.models import LeaveRequest, LeaveBalance, LeaveType, LeavePolicy, LeaveGradeEntitlement
from users.models import CustomUser, Department, Affiliate, EmploymentGrade
from django.utils import timezone

User = get_user_model()


def wipe_all_user_data():
    """
    Completely wipe all user data while preserving app structure.
    """
    print("\n" + "="*70)
    print("🗑️  COMPLETE DATABASE CLEANUP - Starting...")
    print("   This will DELETE ALL users and personal data!")
    print("="*70 + "\n")
    
    try:
        with transaction.atomic():
            # Count everything before deletion
            stats = {
                'users': User.objects.count(),
                'superusers': User.objects.filter(is_superuser=True).count(),
                'requests': LeaveRequest.objects.count(),
                'balances': LeaveBalance.objects.count(),
                'departments': Department.objects.count(),
                'affiliates': Affiliate.objects.count(),
                'leave_types': LeaveType.objects.count(),
            }
            
            print(f"📊 Before Cleanup:")
            print(f"   - Total Users: {stats['users']} (preserving {stats['superusers']} superusers)")
            print(f"   - Leave Requests: {stats['requests']}")
            print(f"   - Leave Balances: {stats['balances']}")
            print(f"   - Departments: {stats['departments']} (preserving)")
            print(f"   - Affiliates: {stats['affiliates']} (preserving)")
            print(f"   - Leave Types: {stats['leave_types']} (preserving)\n")
            
            # Step 1: Delete all leave-related data first (foreign key dependencies)
            print("🗑️  Step 1: Deleting all leave requests...")
            deleted_requests = LeaveRequest.objects.all().delete()
            print(f"   ✓ Deleted {deleted_requests[0]} leave requests")
            
            print("🗑️  Step 2: Deleting all leave balances...")
            deleted_balances = LeaveBalance.objects.all().delete()
            print(f"   ✓ Deleted {deleted_balances[0]} leave balance records")
            
            # Step 2: Try to delete notifications if the model exists
            try:
                from notifications.models import Notification
                print("🗑️  Step 3: Deleting all notifications...")
                deleted_notifications = Notification.objects.all().delete()
                print(f"   ✓ Deleted {deleted_notifications[0]} notifications")
            except ImportError:
                print("   ℹ️  No notification model found, skipping...")
            
            # Step 3: Delete all non-superuser accounts
            print("🗑️  Step 4: Deleting all regular user accounts...")
            regular_users = User.objects.filter(is_superuser=False)
            usernames = list(regular_users.values_list('username', flat=True))
            deleted_users = regular_users.delete()
            actual_deleted = deleted_users[0] if deleted_users else 0
            print(f"   ✓ Deleted {actual_deleted} user accounts:")
            for i, username in enumerate(usernames[:10]):  # Show first 10
                print(f"     - {username}")
            if len(usernames) > 10:
                print(f"     ... and {len(usernames) - 10} more")
            
            # Step 4: Clean up any orphaned data
            print("🗑️  Step 5: Cleaning up any remaining user-related data...")
            
            # Remove any department HOD assignments that might reference deleted users
            hod_updates = 0
            for dept in Department.objects.all():
                if dept.hod and not User.objects.filter(id=dept.hod.id).exists():
                    dept.hod = None
                    dept.save()
                    hod_updates += 1
            print(f"   ✓ Cleared {hod_updates} orphaned HOD assignments")
            
            # Write detailed marker file
            try:
                marker_dir = '/tmp'
                timestamp = int(timezone.now().timestamp())
                marker_path = os.path.join(marker_dir, f'complete_wipe_{timestamp}.txt')
                with open(marker_path, 'w') as mf:
                    mf.write(f"complete_wipe_at={timezone.now().isoformat()}\n")
                    mf.write(f"deleted_users={actual_deleted}\n")
                    mf.write(f"deleted_requests={stats['requests']}\n")
                    mf.write(f"deleted_balances={stats['balances']}\n")
                    mf.write(f"preserved_superusers={stats['superusers']}\n")
                    mf.write(f"preserved_departments={stats['departments']}\n")
                    mf.write(f"preserved_affiliates={stats['affiliates']}\n")
                    mf.write(f"preserved_leave_types={stats['leave_types']}\n")
                    mf.write("\nDeleted usernames:\n")
                    for username in usernames:
                        mf.write(f"  {username}\n")
                print(f"   ✓ Wrote detailed log: {marker_path}")
            except Exception as e:
                print(f"   ⚠️  Failed to write marker file: {e}")
            
            # Final verification
            final_stats = {
                'remaining_users': User.objects.count(),
                'remaining_superusers': User.objects.filter(is_superuser=True).count(),
                'remaining_requests': LeaveRequest.objects.count(),
                'remaining_balances': LeaveBalance.objects.count(),
            }
            
            print("\n" + "="*70)
            print("✅ COMPLETE DATABASE CLEANUP FINISHED")
            print("="*70)
            print(f"\n📊 After Cleanup:")
            print(f"   - Remaining Users: {final_stats['remaining_users']} (all superusers)")
            print(f"   - Remaining Requests: {final_stats['remaining_requests']}")
            print(f"   - Remaining Balances: {final_stats['remaining_balances']}")
            print(f"\n📁 Preserved Structure:")
            print(f"   - Departments: {Department.objects.count()}")
            print(f"   - Affiliates: {Affiliate.objects.count()}")
            print(f"   - Leave Types: {LeaveType.objects.count()}")
            print(f"   - Employment Grades: {EmploymentGrade.objects.count() if hasattr(EmploymentGrade.objects, 'count') else 'N/A'}")
            
            print(f"\n🎯 Database is now completely clean!")
            print("   Ready for fresh user imports via CSV or seeding commands.\n")
            
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR during cleanup: {str(e)}")
        print("   Transaction rolled back - no changes applied.\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n" + "⚠️ "*30)
    print("CRITICAL WARNING: COMPLETE DATABASE WIPE")
    print("⚠️ "*30)
    print("\nThis script will PERMANENTLY DELETE:")
    print("  ❌ ALL user accounts (except superusers)")
    print("  ❌ ALL employee personal information") 
    print("  ❌ ALL leave requests and history")
    print("  ❌ ALL leave balances and entitlements")
    print("  ❌ ALL notifications and user-related data")
    print("\nThis will PRESERVE:")
    print("  ✅ Departments and organizational structure")
    print("  ✅ Affiliates (Merban Capital, SDSL, SBL)")
    print("  ✅ Leave types and policies")
    print("  ✅ Superuser accounts")
    print("\n" + "="*70)
    print("This action CANNOT BE UNDONE!")
    print("="*70 + "\n")
    
    confirmation = input('Type "WIPE DATABASE" to proceed (or anything else to cancel): ')
    
    if confirmation.strip() == "WIPE DATABASE":
        print("\n🔥 FINAL WARNING: Starting complete database wipe in 3 seconds...")
        import time
        time.sleep(3)
        success = wipe_all_user_data()
        sys.exit(0 if success else 1)
    else:
        print("\n✅ Database wipe cancelled. No changes made.\n")
        sys.exit(0)