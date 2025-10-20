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
        """Create or update the CEO user using env vars or provided args.

        Idempotent behavior:
        - If a CEO (role='ceo') already exists, update it with the provided values
        - Else if a user with the provided email exists, update it to be CEO
        - Else create a fresh CEO user
        """
        # Resolve inputs (prefer env vars if present)
        username = options.get('username') or os.getenv('CEO_USERNAME')
        email = options.get('email') or os.getenv('CEO_EMAIL', 'ceo@company.com')
        first_name = options.get('first_name') or os.getenv('CEO_FIRST_NAME', 'Chief')
        last_name = options.get('last_name') or os.getenv('CEO_LAST_NAME', 'Executive Officer')
        password = options.get('password') or os.getenv('CEO_PASSWORD')  # optional for update
        employee_id = options.get('employee_id') or 'CEO001'

        # Derive username from email if missing
        if not username and email:
            username = email.split('@')[0]

        self.stdout.write(f"Ensuring CEO user exists (email: {email})")

        # Ensure Executive department exists
        executive_dept, _ = Department.objects.get_or_create(
            name='Executive',
            defaults={'description': 'Executive leadership team'}
        )

        # Pick target user: existing CEO by role, else by email
        target_user = User.objects.filter(role='ceo').first()
        if not target_user:
            target_user = User.objects.filter(email=email).first()

        if target_user:
            # Update existing user to be CEO with provided details
            target_user.username = username or target_user.username
            target_user.email = email or target_user.email
            target_user.first_name = first_name
            target_user.last_name = last_name
            setattr(target_user, 'role', 'ceo')
            if hasattr(target_user, 'department'):
                setattr(target_user, 'department', executive_dept)
            target_user.is_active = True
            target_user.is_staff = True
            if hasattr(target_user, 'is_active_employee'):
                setattr(target_user, 'is_active_employee', True)
            if password:
                target_user.set_password(password)
            target_user.save()

            dept_name = None
            if hasattr(target_user, 'department'):
                dept = getattr(target_user, 'department', None)
                dept_name = getattr(dept, 'name', 'Executive') if dept else 'Executive'
            msg = (
                "Updated existing CEO user:\n"
                f"  Username: {target_user.username}\n"
                f"  Email: {target_user.email}\n"
                f"  Department: {dept_name or 'Executive'}\n"
            )
            if password:
                msg += "  Password: Updated from environment\n"
            else:
                msg += "  Password: Unchanged (no CEO_PASSWORD provided)\n"
            self.stdout.write(self.style.SUCCESS(msg))
            return

        # Create a new CEO user (ensure unique employee_id)
        unique_emp_id = employee_id
        if User.objects.filter(employee_id=unique_emp_id).exists():
            # Find next available CEO number
            base = "CEO"
            n = 1
            while True:
                candidate = f"{base}{n:03d}"
                if not User.objects.filter(employee_id=candidate).exists():
                    unique_emp_id = candidate
                    break
                n += 1

        ceo_user = User.objects.create_user(
            username=username or 'ceo',
            email=email,
            password=password or 'ChangeMe123!',
            first_name=first_name,
            last_name=last_name,
            employee_id=unique_emp_id,
            role='ceo',
            department=executive_dept,
            is_staff=True,
            annual_leave_entitlement=30,
            is_active_employee=True
        )
        dept_name_created = None
        if hasattr(ceo_user, 'department'):
            dept_c = getattr(ceo_user, 'department', None)
            dept_name_created = getattr(dept_c, 'name', 'Executive') if dept_c else 'Executive'

        self.stdout.write(
            self.style.SUCCESS(
                "Created CEO user:\n"
                f"  Username: {ceo_user.username}\n"
                f"  Email: {ceo_user.email}\n"
                f"  Employee ID: {unique_emp_id}\n"
                f"  Department: {dept_name_created or 'Executive'}\n"
                f"  Password: {'Set from environment' if password else 'ChangeMe123! (temporary)'}\n"
            )
        )