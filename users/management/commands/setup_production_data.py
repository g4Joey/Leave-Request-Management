import os
import json
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

            # Optional bulk user seeding via SEED_USERS environment variable (JSON array)
            seed_users_raw = os.environ.get('SEED_USERS')
            if seed_users_raw:
                try:
                    users_data = json.loads(seed_users_raw)
                    if not isinstance(users_data, list):
                        raise ValueError('SEED_USERS must be a JSON array')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Invalid SEED_USERS JSON: {e}'))
                    users_data = []

                # Preload departments map
                dept_map = {d.name: d for d in Department.objects.all()}
                created_count = 0
                updated_count = 0
                for u in users_data:
                    if not isinstance(u, dict):
                        continue
                    username = u.get('username')
                    if not username:
                        continue
                    role = u.get('role', 'staff')
                    first_name = u.get('first_name', '')
                    last_name = u.get('last_name', '')
                    employee_id = u.get('employee_id') or f'AUTO_{username}'.upper()
                    email = u.get('email') or f'{username}@example.com'
                    dept_name = u.get('department')
                    manager_username = u.get('manager')
                    password = u.get('password')  # only set on create; never override existing

                    dept_obj = None
                    if dept_name:
                        dept_obj = dept_map.get(dept_name)
                        if not dept_obj:
                            dept_obj, _c = Department.objects.get_or_create(name=dept_name, defaults={'description': ''})
                            dept_map[dept_name] = dept_obj

                    manager_obj = None
                    if manager_username:
                        manager_obj = CustomUser.objects.filter(username=manager_username).first()

                    user, created = CustomUser.objects.get_or_create(
                        username=username,
                        defaults={
                            'role': role,
                            'first_name': first_name,
                            'last_name': last_name,
                            'employee_id': employee_id,
                            'email': email,
                            'department': dept_obj,
                            'manager': manager_obj,
                        }
                    )
                    if created:
                        if password:
                            user.set_password(password)
                        else:
                            # Generate a non-guessable unusable password if not provided
                            user.set_unusable_password()
                        user.save()
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f"Seeded new user '{username}' (role={role})."))
                    else:
                        # Update non-sensitive fields only
                        updates = {}
                        fields = [
                            ('role', role),
                            ('first_name', first_name),
                            ('last_name', last_name),
                            ('department', dept_obj),
                            ('manager', manager_obj),
                            ('email', email),
                        ]
                        for field_name, val in fields:
                            if getattr(user, field_name) != val and val is not None:
                                updates[field_name] = val
                        if updates:
                            CustomUser.objects.filter(pk=user.pk).update(**updates)
                            updated_count += 1
                            self.stdout.write(f"Updated user '{username}' fields: {', '.join(updates.keys())}")
                if users_data:
                    self.stdout.write(self.style.SUCCESS(f'SEED_USERS processing complete: {created_count} created, {updated_count} updated.'))
            else:
                self.stdout.write('No SEED_USERS env var detected; skipping bulk user seeding.')

            self.stdout.write(self.style.SUCCESS('Production data setup completed.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Production data setup failed: {e}'))
            raise