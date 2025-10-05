"""
Comprehensive fix for user reference mismatches in leave balances and requests
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from leaves.models import LeaveBalance, LeaveRequest
from django.db import transaction
from django.utils import timezone

class Command(BaseCommand):
    help = 'Fix all user references in leave balances and requests'

    def handle(self, *args, **options):
        User = get_user_model()
        current_year = timezone.now().year
        
        self.stdout.write('Starting comprehensive user reference fix...')
        
        # Get all users
        users = list(User.objects.all())
        self.stdout.write(f'Found {len(users)} users total')
        
        # Show current state
        balances = LeaveBalance.objects.filter(year=current_year)
        requests = LeaveRequest.objects.all()
        self.stdout.write(f'Found {balances.count()} leave balances for {current_year}')
        self.stdout.write(f'Found {requests.count()} leave requests total')
        
        with transaction.atomic():
            # Step 1: Create mapping of old usernames to new email-based users
            username_to_email_user = {}
            
            # Find email-based users (these are the correct ones)
            email_users = []
            username_users = []
            
            for user in users:
                if '@' in user.username:
                    email_users.append(user)
                    # Extract username part from email
                    base_username = user.username.split('@')[0]
                    username_to_email_user[base_username] = user
                else:
                    username_users.append(user)
            
            self.stdout.write(f'Email-based users: {len(email_users)}')
            self.stdout.write(f'Username-based users: {len(username_users)}')
            
            # Step 2: Fix leave balances
            balances_fixed = 0
            for balance in balances:
                old_user = balance.employee
                if old_user.username in username_to_email_user:
                    new_user = username_to_email_user[old_user.username]
                    if old_user != new_user:
                        self.stdout.write(f'Fixing balance: {old_user.username} -> {new_user.username}')
                        balance.employee = new_user
                        balance.save()
                        balances_fixed += 1
            
            # Step 3: Fix leave requests  
            requests_fixed = 0
            for request in requests:
                old_user = request.employee
                if old_user.username in username_to_email_user:
                    new_user = username_to_email_user[old_user.username]
                    if old_user != new_user:
                        self.stdout.write(f'Fixing request: {old_user.username} -> {new_user.username}')
                        request.employee = new_user
                        request.save()
                        requests_fixed += 1
            
            # Step 4: Clean up old username-only users if they have no data
            users_cleaned = 0
            for user in username_users:
                if user.username in username_to_email_user:
                    # Check if this user has any remaining data
                    remaining_balances = LeaveBalance.objects.filter(employee=user).count()
                    remaining_requests = LeaveRequest.objects.filter(employee=user).count()
                    
                    if remaining_balances == 0 and remaining_requests == 0:
                        self.stdout.write(f'Cleaning up old user: {user.username}')
                        user.delete()
                        users_cleaned += 1
                    else:
                        self.stdout.write(f'Keeping user {user.username} - has {remaining_balances} balances, {remaining_requests} requests')
        
        # Final status
        final_users = User.objects.all().count()
        final_balances = LeaveBalance.objects.filter(year=current_year).count()
        final_requests = LeaveRequest.objects.all().count()
        
        self.stdout.write(self.style.SUCCESS(f'''
Comprehensive fix completed!
- Leave balances fixed: {balances_fixed}
- Leave requests fixed: {requests_fixed}
- Old users cleaned up: {users_cleaned}
- Final user count: {final_users}
- Final balance count: {final_balances}
- Final request count: {final_requests}
        '''))