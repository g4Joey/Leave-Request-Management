import os
import json
from pathlib import Path
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

            # Seed additional users from SEED_USERS or SEED_USERS_FILE (idempotent, no password overwrite)
            raw_seed = os.environ.get('SEED_USERS')
            seed_file_path = os.environ.get('SEED_USERS_FILE')
            users_payload = []
            if seed_file_path and Path(seed_file_path).is_file():
                try:
                    users_payload = json.loads(Path(seed_file_path).read_text(encoding='utf-8'))
                    self.stdout.write(f"Loaded SEED_USERS from file: {seed_file_path}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Failed to load SEED_USERS_FILE '{seed_file_path}': {e}"))
            elif raw_seed:
                try:
                    users_payload = json.loads(raw_seed)
                    self.stdout.write("Loaded SEED_USERS from environment variable.")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Invalid SEED_USERS JSON in env: {e}"))

            if users_payload and not isinstance(users_payload, list):
                self.stdout.write(self.style.WARNING('SEED_USERS payload is not a list; skipping user seeding.'))
                users_payload = []

            created_count = 0
            updated_count = 0
            for entry in users_payload:
                if not isinstance(entry, dict):
                    continue
                username = entry.get('username')
                password = entry.get('password')  # Only used on create
                if not username:
                    continue
                defaults = {
                    'email': entry.get('email') or f"{username}@example.com",
                    'first_name': entry.get('first_name') or '',
                    'last_name': entry.get('last_name') or '',
                    'employee_id': entry.get('employee_id') or '',
                    'role': entry.get('role') or 'staff',
                }
                # Map department by name if provided
                dept_name = entry.get('department')
                if dept_name:
                    dept = Department.objects.filter(name=dept_name).first()
                    if dept:
                        defaults['department'] = dept
                # Manager assignment by username (if provided)
                manager_username = entry.get('manager')
                if manager_username:
                    manager = CustomUser.objects.filter(username=manager_username).first()
                    if manager:
                        defaults['manager'] = manager
                user, created = CustomUser.objects.get_or_create(username=username, defaults=defaults)
                if created:
                    if password:
                        user.set_password(password)
                    user.save()
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Seeded user: {username}"))
                else:
                    # Update mutable profile fields but never override password
                    update_fields = {}
                    for k, v in defaults.items():
                        if v and getattr(user, k, None) != v:
                            setattr(user, k, v)
                            update_fields[k] = v
                    if update_fields:
                        user.save(update_fields=list(update_fields.keys()))
                        updated_count += 1
            if users_payload:
                self.stdout.write(self.style.SUCCESS(f"User seeding complete: created={created_count}, updated={updated_count}"))
            else:
                self.stdout.write('No SEED_USERS payload provided or valid; skipping additional user seeding.')

            self.stdout.write(self.style.SUCCESS('Production data setup completed.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Production data setup failed: {e}'))
            raise