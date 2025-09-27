from django.core.management.base import BaseCommand
from users.models import CustomUser
from leaves.models import LeaveType, LeaveBalance
from django.utils import timezone


class Command(BaseCommand):
    help = 'Ensure all active users have leave balances for all leave types (idempotent).'

    def handle(self, *args, **options):
        self.stdout.write('Ensuring all users have complete leave balances...')
        
        current_year = timezone.now().year
        active_users = CustomUser.objects.filter(is_active=True, is_active_employee=True)
        leave_types = LeaveType.objects.filter(is_active=True)
        
        created_count = 0
        updated_count = 0
        
        for user in active_users:
            self.stdout.write(f'Processing user: {user.username} ({user.get_full_name()})')
            
            for leave_type in leave_types:
                balance, created = LeaveBalance.objects.get_or_create(
                    employee=user,
                    leave_type=leave_type,
                    year=current_year,
                    defaults={
                        'entitled_days': self._get_default_entitlement(user, leave_type),
                        'used_days': 0,
                        'pending_days': 0,
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        f'  Created {leave_type.name} balance: {balance.entitled_days} days'
                    )
                else:
                    # Update balance calculations
                    balance.update_balance()
                    updated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Leave balance setup complete: {created_count} created, {updated_count} updated.'
            )
        )
    
    def _get_default_entitlement(self, user, leave_type):
        """Calculate default entitlement based on leave type and user role."""
        if leave_type.name.lower() in ['annual', 'annual leave']:
            # Use user's configured entitlement or default
            return getattr(user, 'annual_leave_entitlement', 25)
        elif leave_type.name.lower() in ['sick', 'sick leave']:
            # Sick leave typically 10-14 days
            return 14 if user.role in ['manager', 'admin', 'hr'] else 10
        elif leave_type.name.lower() in ['maternity', 'maternity leave']:
            # Maternity leave typically 84-90 days
            return 90 if user.role in ['manager', 'admin', 'hr'] else 84
        elif leave_type.name.lower() in ['paternity', 'paternity leave']:
            # Paternity leave typically 7-14 days
            return 14 if user.role in ['manager', 'admin', 'hr'] else 7
        elif leave_type.name.lower() in ['compassionate', 'compassionate leave']:
            # Compassionate leave typically 3-5 days
            return 5
        elif leave_type.name.lower() in ['casual', 'casual leave']:
            # Casual leave typically 5-7 days
            return 7 if user.role in ['manager', 'admin', 'hr'] else 5
        else:
            # Default fallback
            return 10