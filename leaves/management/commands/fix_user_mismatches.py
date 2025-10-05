"""
Management command to fix user/leave balance mismatches
This fixes cases where users log in with emails but leave balances are tied to usernames
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from leaves.models import LeaveBalance, LeaveRequest

User = get_user_model()

class Command(BaseCommand):
    help = 'Fix user/leave balance mismatches by linking email logins to username-based balances'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== FIXING USER/LEAVE BALANCE MISMATCHES ==='))
        
        # Map email-based logins to username-based data
        email_to_username_mapping = {
            'gsafo@umbcapital.com': 'gsafo',
            'aakorfu@umbcapital.com': 'aakorfu', 
            'jmankoe@umbcapital.com': 'jmankoe',
            'hr@umbcapital.com': 'hr_admin',
            'admin@company.com': 'admin@company.com',  # This one should match
        }
        
        current_year = timezone.now().year
        fixed_count = 0
        
        for email, username in email_to_username_mapping.items():
            # Find user by email
            email_user = User.objects.filter(email=email).first()
            # Find user by username
            username_user = User.objects.filter(username=username).first()
            
            if email_user and username_user and email_user != username_user:
                self.stdout.write(f'Found mismatch: email user {email_user.username} vs username user {username_user.username}')
                
                # Transfer leave balances from username_user to email_user
                balances = LeaveBalance.objects.filter(employee=username_user, year=current_year)
                requests = LeaveRequest.objects.filter(employee=username_user)
                
                self.stdout.write(f'  Transferring {balances.count()} balances and {requests.count()} requests...')
                
                # Update the foreign keys to point to the email_user
                balances.update(employee=email_user)
                requests.update(employee=email_user)
                
                # Update email_user with username_user's data if needed
                if not email_user.first_name and username_user.first_name:
                    email_user.first_name = username_user.first_name
                if not email_user.last_name and username_user.last_name:
                    email_user.last_name = username_user.last_name
                if not email_user.role and username_user.role:
                    email_user.role = username_user.role
                
                email_user.save()
                
                # Delete the username_user to avoid confusion
                username_user.delete()
                
                fixed_count += 1
                self.stdout.write(self.style.SUCCESS(f'  Fixed: {email} now owns data from {username}'))
            
            elif not email_user and username_user:
                # Create email user from username user
                self.stdout.write(f'Creating email user for {email} from {username}')
                
                new_user = User.objects.create(
                    username=email,
                    email=email,
                    first_name=username_user.first_name,
                    last_name=username_user.last_name,
                    role=username_user.role,
                    is_active=True,
                    is_active_employee=True,
                    is_superuser=username_user.is_superuser,
                    is_staff=username_user.is_staff,
                )
                new_user.set_password('password123')
                new_user.save()
                
                # Transfer data
                balances = LeaveBalance.objects.filter(employee=username_user, year=current_year)
                requests = LeaveRequest.objects.filter(employee=username_user)
                
                balances.update(employee=new_user)
                requests.update(employee=new_user)
                
                # Delete old user
                username_user.delete()
                
                fixed_count += 1
                self.stdout.write(self.style.SUCCESS(f'  Created and fixed: {email} with password123'))
        
        self.stdout.write(self.style.SUCCESS(f'=== FIXED {fixed_count} USER MISMATCHES ==='))
        
        # Show final state
        users = User.objects.filter(is_active=True)
        self.stdout.write(f'Final user count: {users.count()}')
        for user in users:
            balances = LeaveBalance.objects.filter(employee=user, year=current_year).count()
            self.stdout.write(f'  {user.username} ({user.email}) - {balances} leave balances')