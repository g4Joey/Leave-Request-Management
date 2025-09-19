from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from leaves.models import LeaveType, LeaveBalance, LeaveRequest
from datetime import date, timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Create test data for the leave management system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing test data before creating new data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing test data...')
            LeaveRequest.objects.all().delete()
            LeaveBalance.objects.all().delete()
            LeaveType.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        # Create leave types
        self.stdout.write('Creating leave types...')
        annual_leave, created = LeaveType.objects.get_or_create(
            name='Annual Leave',
            defaults={
                'description': 'Yearly vacation leave',
                'max_days_per_request': 25,
                'is_active': True
            }
        )
        
        sick_leave, created = LeaveType.objects.get_or_create(
            name='Sick Leave',
            defaults={
                'description': 'Medical leave for illness',
                'max_days_per_request': 15,
                'requires_medical_certificate': True,
                'is_active': True
            }
        )
        
        personal_leave, created = LeaveType.objects.get_or_create(
            name='Personal Leave',
            defaults={
                'description': 'Personal time off',
                'max_days_per_request': 10,
                'is_active': True
            }
        )

        # Create test users
        self.stdout.write('Creating test users...')
        
        # Create employees
        employee1, created = User.objects.get_or_create(
            email='john.doe@company.com',
            defaults={
                'username': 'john.doe',
                'first_name': 'John',
                'last_name': 'Doe',
                'role': 'staff',
                'employee_id': 'EMP001',
                'hire_date': date(2023, 1, 15),
                'is_active': True
            }
        )
        if created:
            employee1.set_password('password123')
            employee1.save()

        employee2, created = User.objects.get_or_create(
            email='jane.smith@company.com',
            defaults={
                'username': 'jane.smith',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'role': 'staff',
                'employee_id': 'EMP002',
                'hire_date': date(2022, 6, 1),
                'is_active': True
            }
        )
        if created:
            employee2.set_password('password123')
            employee2.save()

        # Create manager
        manager, created = User.objects.get_or_create(
            email='manager@company.com',
            defaults={
                'username': 'manager',
                'first_name': 'Mike',
                'last_name': 'Manager',
                'role': 'manager',
                'employee_id': 'MGR001',
                'hire_date': date(2021, 3, 1),
                'is_active': True
            }
        )
        if created:
            manager.set_password('password123')
            manager.save()

        # Create HR user
        hr_user, created = User.objects.get_or_create(
            email='hr@company.com',
            defaults={
                'username': 'hr.admin',
                'first_name': 'HR',
                'last_name': 'Admin',
                'role': 'hr',
                'employee_id': 'HR001',
                'hire_date': date(2020, 1, 1),
                'is_active': True
            }
        )
        if created:
            hr_user.set_password('password123')
            hr_user.save()

        # Create leave balances for 2025
        self.stdout.write('Creating leave balances...')
        current_year = timezone.now().year
        
        users = [employee1, employee2, manager, hr_user]
        leave_types = [annual_leave, sick_leave, personal_leave]
        
        for user in users:
            for leave_type in leave_types:
                LeaveBalance.objects.get_or_create(
                    employee=user,
                    leave_type=leave_type,
                    year=current_year,
                    defaults={
                        'entitled_days': 25,  # Standard entitlement
                        'used_days': 0,
                        'pending_days': 0
                    }
                )

        # Create some sample leave requests
        self.stdout.write('Creating sample leave requests...')
        
        # Employee1 - Approved annual leave
        LeaveRequest.objects.get_or_create(
            employee=employee1,
            leave_type=annual_leave,
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 5),
            defaults={
                'reason': 'Family vacation',
                'status': 'approved',
                'approved_by': manager,
                'approval_comments': 'Approved - enjoy your vacation!',
                'total_days': 5
            }
        )
        
        # Employee1 - Pending sick leave
        LeaveRequest.objects.get_or_create(
            employee=employee1,
            leave_type=sick_leave,
            start_date=date(2025, 9, 25),
            end_date=date(2025, 9, 26),
            defaults={
                'reason': 'Medical appointment',
                'status': 'pending',
                'total_days': 2
            }
        )
        
        # Employee2 - Pending personal leave
        LeaveRequest.objects.get_or_create(
            employee=employee2,
            leave_type=personal_leave,
            start_date=date(2025, 10, 15),
            end_date=date(2025, 10, 15),
            defaults={
                'reason': 'Personal errands',
                'status': 'pending',
                'total_days': 1
            }
        )

        # Update leave balances based on approved requests
        self.stdout.write('Updating leave balances...')
        approved_requests = LeaveRequest.objects.filter(status='approved')
        for request in approved_requests:
            try:
                balance = LeaveBalance.objects.get(
                    employee=request.employee,
                    leave_type=request.leave_type,
                    year=request.start_date.year
                )
                balance.used_days += request.total_days
                balance.save()
            except LeaveBalance.DoesNotExist:
                pass

        # Update pending balances
        pending_requests = LeaveRequest.objects.filter(status='pending')
        for request in pending_requests:
            try:
                balance = LeaveBalance.objects.get(
                    employee=request.employee,
                    leave_type=request.leave_type,
                    year=request.start_date.year
                )
                balance.pending_days += request.total_days
                balance.save()
            except LeaveBalance.DoesNotExist:
                pass

        self.stdout.write(
            self.style.SUCCESS('Successfully created test data!')
        )
        
        self.stdout.write('\nTest user credentials:')
        self.stdout.write('Employee 1: john.doe@company.com / password123')
        self.stdout.write('Employee 2: jane.smith@company.com / password123')
        self.stdout.write('Manager: manager@company.com / password123')
        self.stdout.write('HR Admin: hr@company.com / password123')
        
        self.stdout.write(f'\nAPI endpoints available at:')
        self.stdout.write('http://127.0.0.1:8000/api/leaves/')
        self.stdout.write('http://127.0.0.1:8000/api/auth/token/ (for authentication)')