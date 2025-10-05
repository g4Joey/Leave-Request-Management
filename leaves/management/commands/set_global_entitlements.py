"""
Management command to set global leave entitlements for all active employees.
This is useful for initializing the system or applying HR-configured entitlements.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from leaves.models import LeaveType, LeaveBalance


class Command(BaseCommand):
    help = 'Set global leave entitlements for all active employees'

    def add_arguments(self, parser):
        parser.add_argument(
            '--leave-type',
            type=str,
            help='Leave type name to set entitlements for (if not specified, sets for all types)',
        )
        parser.add_argument(
            '--days',
            type=int,
            help='Number of days to set (required if --leave-type is specified)',
        )
        parser.add_argument(
            '--year',
            type=int,
            default=timezone.now().year,
            help='Year to set entitlements for (default: current year)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        current_year = options['year']
        dry_run = options['dry_run']
        
        # Get active employees
        employees = User.objects.filter(is_active=True, is_active_employee=True)
        self.stdout.write(f"Found {employees.count()} active employees")
        
        if options['leave_type']:
            # Set specific leave type
            leave_type_name = options['leave_type']
            days = options['days']
            
            if days is None:
                self.stdout.write(
                    self.style.ERROR('--days is required when --leave-type is specified')
                )
                return
            
            try:
                leave_type = LeaveType.objects.get(name=leave_type_name, is_active=True)
            except LeaveType.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Leave type "{leave_type_name}" not found or inactive')
                )
                return
            
            self.set_entitlement_for_type(leave_type, days, current_year, employees, dry_run)
        else:
            # Set default entitlements for all leave types
            leave_types = LeaveType.objects.filter(is_active=True)
            
            # Default entitlements (you can modify these as needed)
            default_entitlements = {
                'Annual Leave': 25,
                'Sick Leave': 14,
                'Casual Leave': 7,
                'Maternity Leave': 90,
                'Paternity Leave': 14,
                'Compassionate Leave': 5,
            }
            
            for leave_type in leave_types:
                days = default_entitlements.get(leave_type.name, 0)
                if days > 0:
                    self.set_entitlement_for_type(leave_type, days, current_year, employees, dry_run)
                else:
                    self.stdout.write(
                        self.style.WARNING(f'No default entitlement for {leave_type.name}, skipping')
                    )

    def set_entitlement_for_type(self, leave_type, days, year, employees, dry_run):
        self.stdout.write(f"\nSetting {leave_type.name} entitlement to {days} days for {year}")
        
        updated = 0
        created = 0
        
        for employee in employees:
            balance, was_created = LeaveBalance.objects.get_or_create(
                employee=employee,
                leave_type=leave_type,
                year=year,
                defaults={'entitled_days': days, 'used_days': 0, 'pending_days': 0}
            )
            
            if was_created:
                if not dry_run:
                    created += 1
                self.stdout.write(
                    f"  {'[DRY RUN] ' if dry_run else ''}Created balance for {employee.username}: {days} days"
                )
            elif balance.entitled_days != days:
                if not dry_run:
                    balance.entitled_days = days
                    balance.save(update_fields=['entitled_days', 'updated_at'])
                    updated += 1
                self.stdout.write(
                    f"  {'[DRY RUN] ' if dry_run else ''}Updated {employee.username}: {balance.entitled_days} -> {days} days"
                )
            else:
                self.stdout.write(f"  No change needed for {employee.username}: {days} days")
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Completed: {created} created, {updated} updated for {leave_type.name}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: Would create {created}, update {updated} for {leave_type.name}")
            )