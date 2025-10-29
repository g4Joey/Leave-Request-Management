from django.core.management.base import BaseCommand
from users.models import CustomUser
from leaves.models import LeaveRequest, LeaveBalance
from django.utils import timezone
from django.db import transaction


class Command(BaseCommand):
    help = 'Reset leave data for seeded users (jmankoe, aakorfu, gsafo)'

    def handle(self, *args, **options):
        """Reset leave data for seeded users"""
        
        # Seeded users to reset
        seeded_usernames = ['jmankoe', 'aakorfu', 'gsafo']
        
    self.stdout.write("[info] Resetting leave data for seeded users")
    self.stdout.write("=" * 50)
        
        total_requests_deleted = 0
        total_balances_reset = 0
        
        with transaction.atomic():
            for username in seeded_usernames:
                try:
                    user = CustomUser.objects.get(username=username)
                    self.stdout.write(f"\nProcessing user: {user.get_full_name()} ({username})")
                    
                    # 1. Delete all leave requests for this user
                    leave_requests = LeaveRequest.objects.filter(employee=user)
                    request_count = leave_requests.count()
                    if request_count > 0:
                        leave_requests.delete()
                        total_requests_deleted += request_count
                        self.stdout.write(f"   Deleted {request_count} leave request(s)")
                    else:
                        self.stdout.write("   No leave requests to delete")
                    
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
                        total_balances_reset += updated
                        self.stdout.write(f"   Reset {updated} leave balance(s) to zero usage")
                        
                        # Show updated balances
                        for balance in leave_balances:
                            balance.refresh_from_db()  # Get updated values
                            self.stdout.write(
                                f"      - {balance.leave_type.name} {balance.year}: {balance.entitled_days} entitled, "
                                f"{balance.used_days} used, {balance.pending_days} pending"
                            )
                    else:
                        self.stdout.write("   No leave balances found")
                    
                except CustomUser.DoesNotExist:
                    self.stdout.write(f"User '{username}' not found in database")
                    continue
        
    self.stdout.write("\nSeeded users leave data reset completed!")
        self.stdout.write(f"   - Users processed: {', '.join(seeded_usernames)}")
        self.stdout.write(f"   - Total leave requests deleted: {total_requests_deleted}")
        self.stdout.write(f"   - Total leave balances reset: {total_balances_reset}")
        self.stdout.write(f"   - Leave entitlements preserved")