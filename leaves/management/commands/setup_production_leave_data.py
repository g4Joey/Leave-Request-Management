from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import CustomUser
from leaves.models import LeaveType, LeaveBalance


class Command(BaseCommand):
    help = 'Ensure production environment has all necessary leave data for users to submit requests.'

    def handle(self, *args, **options):
        self.stdout.write('=== Production Leave Data Setup ===')
        
        # Ensure leave types exist
        self._ensure_leave_types()
        
        # Ensure all users have leave balances
        self._ensure_leave_balances()
        
        # Verify data integrity
        self._verify_setup()
        
        self.stdout.write(self.style.SUCCESS('Production leave data setup completed successfully.'))
    
    def _ensure_leave_types(self):
        """Ensure default leave types exist."""
        self.stdout.write('Checking leave types...')
        
        default_types = [
            ('Annual Leave', 'Annual leave entitlement', 30, False),
            ('Sick Leave', 'Sick leave; may require medical certificate', 14, True),
            ('Maternity Leave', 'Maternity leave', 90, False),
            ('Paternity Leave', 'Paternity leave', 14, False),
            ('Compassionate Leave', 'Compassionate leave', 5, False),
            ('Casual Leave', 'Casual leave', 7, False),
        ]
        
        created_count = 0
        for name, desc, max_days, requires_cert in default_types:
            leave_type, created = LeaveType.objects.get_or_create(
                name=name,
                defaults={
                    'description': desc,
                    'max_days_per_request': max_days,
                    'requires_medical_certificate': requires_cert,
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created leave type: {name}')
        
        total_types = LeaveType.objects.filter(is_active=True).count()
        self.stdout.write(f'✅ Leave types ready: {total_types} active ({created_count} created)')
    
    def _ensure_leave_balances(self):
        """Ensure all active users have leave balances."""
        self.stdout.write('Checking user leave balances...')
        
        current_year = timezone.now().year
        active_users = CustomUser.objects.filter(is_active=True, is_active_employee=True)
        leave_types = LeaveType.objects.filter(is_active=True)
        
        created_count = 0
        for user in active_users:
            for leave_type in leave_types:
                balance, created = LeaveBalance.objects.get_or_create(
                    employee=user,
                    leave_type=leave_type,
                    year=current_year,
                    defaults={
                        'entitled_days': self._get_entitlement(user, leave_type),
                        'used_days': 0,
                        'pending_days': 0,
                    }
                )
                if created:
                    created_count += 1
        
        total_balances = LeaveBalance.objects.filter(year=current_year).count()
        self.stdout.write(f'✅ Leave balances ready: {total_balances} total ({created_count} created)')
    
    def _get_entitlement(self, user, leave_type):
        """Calculate entitlement based on leave type and user."""
        type_name = leave_type.name.lower()
        
        if 'annual' in type_name:
            return getattr(user, 'annual_leave_entitlement', 25)
        elif 'sick' in type_name:
            return 14 if user.role in ['manager', 'admin', 'hr'] else 10
        elif 'maternity' in type_name:
            return 90 if user.role in ['manager', 'admin', 'hr'] else 84
        elif 'paternity' in type_name:
            return 14 if user.role in ['manager', 'admin', 'hr'] else 7
        elif 'compassionate' in type_name:
            return 5
        elif 'casual' in type_name:
            return 7 if user.role in ['manager', 'admin', 'hr'] else 5
        else:
            return 10
    
    def _verify_setup(self):
        """Verify the setup is complete and functional."""
        self.stdout.write('Verifying setup...')
        
        # Check we have active leave types
        leave_types_count = LeaveType.objects.filter(is_active=True).count()
        if leave_types_count == 0:
            raise Exception("No active leave types found!")
        
        # Check we have active users
        users_count = CustomUser.objects.filter(is_active=True, is_active_employee=True).count()
        if users_count == 0:
            raise Exception("No active users found!")
        
        # Check we have leave balances for current year
        current_year = timezone.now().year
        balances_count = LeaveBalance.objects.filter(year=current_year).count()
        expected_balances = users_count * leave_types_count
        
        self.stdout.write(f'  Active leave types: {leave_types_count}')
        self.stdout.write(f'  Active users: {users_count}')
        self.stdout.write(f'  Leave balances: {balances_count} (expected: {expected_balances})')
        
        if balances_count < expected_balances:
            self.stdout.write(self.style.WARNING(f'Missing {expected_balances - balances_count} leave balances'))
        else:
            self.stdout.write('✅ All users have complete leave balances')