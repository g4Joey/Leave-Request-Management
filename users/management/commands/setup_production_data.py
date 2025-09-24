import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from users.models import CustomUser, Department


class Command(BaseCommand):
    help = 'Idempotent production data setup: ensures departments and HR user without overwriting existing passwords.'

    def handle(self, *args, **options):
        self.stdout.write('Running production data setup...')
        try:
            # Ensure base departments and relationships, but never create default HR with local password
            call_command('setup_departments', skip_hr=True)
            # Ensure default leave types exist for HR configuration
            call_command('setup_leave_types')
            # Ensure default leave types are present (idempotent)
            call_command('setup_leave_types')

            # Do not override any existing user passwords in production
            # Only create an HR user if none exists AND explicit credentials are provided via env vars
            existing_hr = CustomUser.objects.filter(role='hr').exists()
            if existing_hr:
                self.stdout.write('HR user already present; skipping HR creation.')
            else:
                username = os.environ.get('HR_ADMIN_USERNAME', 'hr_admin')
                password = os.environ.get('HR_ADMIN_PASSWORD')
                if password:
                    dept = Department.objects.filter(name='Client Service').first()
                    user, created = CustomUser.objects.get_or_create(
                        username=username,
                        defaults={
                            'email': os.environ.get('HR_ADMIN_EMAIL', 'hr@company.com'),
                            'first_name': os.environ.get('HR_ADMIN_FIRST_NAME', 'HR'),
                            'last_name': os.environ.get('HR_ADMIN_LAST_NAME', 'Administrator'),
                            'employee_id': os.environ.get('HR_ADMIN_EMPLOYEE_ID', 'HR001'),
                            'role': 'hr',
                            'department': dept,
                        }
                    )
                    if created:
                        user.set_password(password)
                        user.save()
                        self.stdout.write(self.style.SUCCESS(f"Created HR user '{username}' from env vars."))
                    else:
                        # If user exists already, never override the password
                        self.stdout.write(f"HR username '{username}' exists; not modifying.")
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            'No HR user found and HR_ADMIN_PASSWORD not set. Skipping HR creation to avoid weak defaults. '
                            'Set HR_ADMIN_USERNAME and HR_ADMIN_PASSWORD env vars and redeploy to create HR.'
                        )
                    )

            self.stdout.write(self.style.SUCCESS('Production data setup completed.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Production data setup failed: {e}'))
            raise