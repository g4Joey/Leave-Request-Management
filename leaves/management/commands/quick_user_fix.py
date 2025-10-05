"""
Quick fix to update existing users with proper email/username mapping
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from leaves.models import LeaveBalance
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = 'Quick fix: update user emails to match their usernames for proper authentication'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== QUICK USER EMAIL FIX ==='))
        
        # Update users so their email matches what they use to log in
        updates = [
            {'username': 'gsafo', 'email': 'gsafo@umbcapital.com', 'first_name': 'George', 'last_name': 'Safo'},
            {'username': 'aakorfu', 'email': 'aakorfu@umbcapital.com', 'first_name': 'Augustine', 'last_name': 'Korfu'},
            {'username': 'jmankoe', 'email': 'jmankoe@umbcapital.com', 'first_name': 'Joshua', 'last_name': 'Mankoe'},
            {'username': 'hr_admin', 'email': 'hr@umbcapital.com', 'first_name': 'HR', 'last_name': 'Admin'},
        ]
        
        for update_data in updates:
            user = User.objects.filter(username=update_data['username']).first()
            if user:
                user.email = update_data['email']
                user.first_name = update_data['first_name']
                user.last_name = update_data['last_name']
                if not user.password or user.password == '':
                    user.set_password('password123')
                user.save()
                
                current_year = timezone.now().year
                balances = LeaveBalance.objects.filter(employee=user, year=current_year).count()
                self.stdout.write(f'Updated {user.username} -> {user.email} ({balances} balances)')
            else:
                self.stdout.write(self.style.WARNING(f'User {update_data["username"]} not found'))
        
        # Ensure admin user exists
        admin_user, created = User.objects.get_or_create(
            username='admin@company.com',
            defaults={
                'email': 'admin@company.com',
                'first_name': 'System',
                'last_name': 'Admin',
                'role': 'manager',
                'is_active': True,
                'is_active_employee': True,
                'is_superuser': True,
                'is_staff': True,
            }
        )
        if created or not admin_user.password:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(f'Admin user ready: admin@company.com / admin123')
        
        self.stdout.write(self.style.SUCCESS('=== QUICK FIX COMPLETE ==='))
        
        # Show final state
        current_year = timezone.now().year
        for user in User.objects.filter(is_active=True):
            balances = LeaveBalance.objects.filter(employee=user, year=current_year).count()
            self.stdout.write(f'  {user.username} ({user.email}) - {balances} leave balances')