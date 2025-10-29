#!/usr/bin/env python3
"""
Reset leave data for seeded users (jmankoe, aakorfu, gsafo)
This script clears their leave balances and reverses all leave requests for demo purposes.
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from users.models import CustomUser
from leaves.models import LeaveRequest, LeaveBalance, LeaveType
from django.utils import timezone
from django.db import transaction


def reset_seeded_users_leave_data():
    """Reset leave data for seeded users"""
    
    # Seeded users to reset
    seeded_usernames = ['jmankoe', 'aakorfu', 'gsafo']
    
    print("[info] Resetting leave data for seeded users")
    print("=" * 50)
    
    with transaction.atomic():
        for username in seeded_usernames:
            try:
                user = CustomUser.objects.get(username=username)
                print(f"\nProcessing user: {user.get_full_name()} ({username})")
                
                # 1. Delete all leave requests for this user
                leave_requests = LeaveRequest.objects.filter(employee=user)
                request_count = leave_requests.count()
                if request_count > 0:
                    leave_requests.delete()
                    print(f"   Deleted {request_count} leave request(s)")
                else:
                    print("   No leave requests to delete")
                
                # 2. Reset all leave balances to zero usage
                leave_balances = LeaveBalance.objects.filter(employee=user)
                balance_count = leave_balances.count()
                if balance_count > 0:
                    # Reset used_days and pending_days to 0
                    updated = leave_balances.update(
                        used_days=0,
                        pending_days=0,
                        updated_at=timezone.now()
                    )
                    print(f"   Reset {updated} leave balance(s) to zero usage")
                    
                    # Show updated balances
                    for balance in leave_balances:
                        balance.refresh_from_db()  # Get updated values
                        print(
                            f"      - {balance.leave_type.name} {balance.year}: {balance.entitled_days} entitled, "
                            f"{balance.used_days} used, {balance.pending_days} pending"
                        )
                else:
                    print("   No leave balances found")
                
            except CustomUser.DoesNotExist:
                print(f"User '{username}' not found in database")
                continue
    
    print("\nSeeded users leave data reset completed!")
    print(f"   - Users processed: {', '.join(seeded_usernames)}")
    print(f"   - All leave requests deleted")
    print(f"   - All leave balances reset to zero usage")
    print(f"   - Leave entitlements preserved")


if __name__ == "__main__":
    reset_seeded_users_leave_data()