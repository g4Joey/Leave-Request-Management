"""
Management command to create a CEO user for the three-tier approval system
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Department

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a CEO user for the three-tier approval system'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username for the CEO')
        parser.add_argument('--email', type=str, help='Email for the CEO')
        parser.add_argument('--first-name', type=str, help='First name')
        parser.add_argument('--last-name', type=str, help='Last name')
        parser.add_argument('--password', type=str, help='Password for the CEO')
        parser.add_argument('--employee-id', type=str, default='CEO001', help='Employee ID')

    def handle(self, *args, **options):
        # Use environment variables if available, otherwise use provided options or defaults
        username = options.get('username') or os.getenv('CEO_USERNAME', 'ceo')
        email = options.get('email') or os.getenv('CEO_EMAIL', 'ceo@company.com')
        first_name = options.get('first_name') or os.getenv('CEO_FIRST_NAME', 'Chief')
        last_name = options.get('last_name') or os.getenv('CEO_LAST_NAME', 'Executive Officer')
        password = options.get('password') or os.getenv('CEO_PASSWORD', 'ChangeMe123!')
        employee_id = options.get('employee_id') or 'CEO001'

        # Extract username from email if not provided
        if username == 'ceo' and email != 'ceo@company.com':
            username = email.split('@')[0]

        self.stdout.write(f'Creating CEO user with email: {email}')

        # Check if CEO user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'CEO user with username "{username}" already exists!')
            )
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(f'CEO user with email "{email}" already exists!')
            )
            return

        if User.objects.filter(employee_id=employee_id).exists():
            self.stdout.write(
                self.style.WARNING(f'User with employee ID "{employee_id}" already exists!')
            )
            return

        # Get or create Executive department
        executive_dept, created = Department.objects.get_or_create(
            name='Executive',
            defaults={'description': 'Executive leadership team'}
        )
        if created:
            self.stdout.write(f'Created Executive department')

        # Create CEO user
        ceo_user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            employee_id=employee_id,
            role='ceo',
            department=executive_dept,
            is_staff=True,  # CEO should have admin access
            annual_leave_entitlement=30,  # CEO gets more leave
            is_active_employee=True
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created CEO user:\n'
                f'  Username: {username}\n'
                f'  Email: {email}\n'
                f'  Employee ID: {employee_id}\n'
                f'  Password: {"Set from environment" if os.getenv("CEO_PASSWORD") else "ChangeMe123!"}\n'
                f'  Role: {getattr(ceo_user, "role", "ceo")}\n'
                f'  Department: {getattr(ceo_user.department, "name", "Executive")}\n\n'
                f'CEO user ready for production use!'
            )
        )