from django.core.management.base import BaseCommand
from users.models import CustomUser


class Command(BaseCommand):
    help = 'Fix user activation flags to ensure users can login'

    def handle(self, *args, **options):
        self.stdout.write('Checking and fixing user activation flags...')
        
        # Find users who are active but not active_employee (or vice versa)
        users_to_fix = CustomUser.objects.filter(
            is_active=True, 
            is_active_employee=False
        )
        
        count = users_to_fix.count()
        if count > 0:
            users_to_fix.update(is_active_employee=True)
            self.stdout.write(f'Fixed {count} users with missing is_active_employee flag')
            
            for user in users_to_fix:
                self.stdout.write(f'  - {user.username} ({user.email})')
        else:
            self.stdout.write('All active users already have is_active_employee=True')
        
        # Also ensure demo users are properly activated
        demo_usernames = ['ato_manager', 'george_staff', 'augustine_staff', 'hr_admin']
        demo_users = CustomUser.objects.filter(username__in=demo_usernames)
        
        for user in demo_users:
            updated = False
            if not user.is_active:
                user.is_active = True
                updated = True
            if not user.is_active_employee:
                user.is_active_employee = True
                updated = True
            if updated:
                user.save()
                self.stdout.write(f'Activated demo user: {user.username}')
        
        self.stdout.write(self.style.SUCCESS('User activation check completed.'))