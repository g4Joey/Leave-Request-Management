from django.core.management.base import BaseCommand
from users.models import CustomUser
from leaves.models import LeaveBalance, LeaveRequest, LeaveType
from django.utils import timezone

class Command(BaseCommand):
    help = 'Fix production data: keep only Ato as manager, remove other managers, and ensure leave balances.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting production data fix...'))
        
        # 1. Keep only jmankoe as manager
        ato = CustomUser.objects.filter(username='jmankoe').first()
        if not ato:
            self.stdout.write(self.style.ERROR('Ato (jmankoe) not found!'))
            return
        managers = CustomUser.objects.filter(role='manager').exclude(username='jmankoe')
        manager_count = managers.count()
        for manager in managers:
            # Remove leave balances and requests if needed
            LeaveBalance.objects.filter(employee=manager).delete()
            LeaveRequest.objects.filter(employee=manager).delete()
            # Optionally, delete the user
            manager.delete()
            self.stdout.write(self.style.SUCCESS(f'Removed manager: {manager.username}'))
        self.stdout.write(self.style.SUCCESS(f'Removed {manager_count} extra managers. Only Ato remains as manager.'))

        # 2. Ensure leave balances for all active employees for current year
        current_year = timezone.now().year
        self.stdout.write(f'Creating leave balances for year {current_year}...')
        
        # Get all active employees
        employees = CustomUser.objects.filter(is_active=True, is_active_employee=True)
        self.stdout.write(f'Found {employees.count()} active employees')
        
        # Get all active leave types
        leave_types = LeaveType.objects.filter(is_active=True)
        self.stdout.write(f'Found {leave_types.count()} active leave types')
        
        # Default entitlements
        default_entitlements = {
            'Annual Leave': 25,
            'Sick Leave': 14,
            'Casual Leave': 7,
            'Maternity Leave': 90,
            'Paternity Leave': 14,
            'Compassionate Leave': 5,
        }
        
        created_count = 0
        updated_count = 0
        
        for leave_type in leave_types:
            days = default_entitlements.get(leave_type.name, 0)
            if days > 0:
                self.stdout.write(f'Setting {leave_type.name} entitlement to {days} days...')
                
                for employee in employees:
                    balance, was_created = LeaveBalance.objects.get_or_create(
                        employee=employee,
                        leave_type=leave_type,
                        year=current_year,
                        defaults={'entitled_days': days, 'used_days': 0, 'pending_days': 0}
                    )
                    
                    if was_created:
                        created_count += 1
                        self.stdout.write(f'  Created balance for {employee.username}: {days} days')
                    elif balance.entitled_days != days:
                        balance.entitled_days = days
                        balance.save(update_fields=['entitled_days', 'updated_at'])
                        updated_count += 1
                        self.stdout.write(f'  Updated {employee.username}: {balance.entitled_days} -> {days} days')
            else:
                self.stdout.write(self.style.WARNING(f'No default entitlement for {leave_type.name}, skipping'))
        
        self.stdout.write(self.style.SUCCESS(f'Leave balances complete: {created_count} created, {updated_count} updated'))
        
        # 3. Verify the data
        total_balances = LeaveBalance.objects.filter(year=current_year).count()
        self.stdout.write(self.style.SUCCESS(f'Total leave balances in database for {current_year}: {total_balances}'))
