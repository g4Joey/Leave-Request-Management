from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import Department, CustomUser
import os


class Command(BaseCommand):
    help = 'Create departments and assign staff with approvers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-hr',
            action='store_true',
            help='Skip creating HR user (useful for production environments)'
        )

    def handle(self, *args, **options):
        self.stdout.write('Creating departments and staff assignments...')
        skip_hr = options.get('skip_hr')
        
        with transaction.atomic():
            # Create departments
            departments_data = [
                ('Accounts & Compliance', 'Financial accounts and regulatory compliance'),
                ('IHL', 'Investment and Holdings Limited'),
                ('Stockbrokers', 'Stock brokerage services'),
                # SDSL is Strategic Debts Solution Limited
                ('SDSL', 'Strategic Debts Solution Limited'),
                ('Client Service', 'Customer service and support'),
                ('Pensions', 'Pension fund management'),
                ('Government Securities', 'Government securities trading'),
                ('Marketing', 'Marketing and communications'),
                ('IT', 'Information Technology services'),
            ]
            
            created_departments = {}
            for dept_name, dept_desc in departments_data:
                dept, created = Department.objects.get_or_create(
                    name=dept_name,
                    defaults={'description': dept_desc}
                )
                created_departments[dept_name] = dept
                if created:
                    self.stdout.write(f'Created department: {dept_name}')
                else:
                    self.stdout.write(f'Department already exists: {dept_name}')
                # Keep department description up-to-date (idempotent)
                if dept.description != dept_desc:
                    Department.objects.filter(pk=dept.pk).update(description=dept_desc)
                    self.stdout.write(f'Updated description for department: {dept_name}')
            
            # If an old combined department exists, migrate/rename to IT
            mit_dept = Department.objects.filter(name='Marketing and IT').first()
            it_dept = created_departments.get('IT')
            marketing_dept = created_departments.get('Marketing')

            if mit_dept:
                if not it_dept:
                    # Rename the old combined department to IT
                    mit_dept.name = 'IT'
                    mit_dept.description = mit_dept.description or 'Information Technology services'
                    mit_dept.save(update_fields=['name', 'description'])
                    it_dept = mit_dept
                    self.stdout.write('Renamed department "Marketing and IT" to "IT"')
                else:
                    # Move any users from the old combined department to IT
                    moved = CustomUser.objects.filter(department=mit_dept).update(department=it_dept)
                    self.stdout.write(f'Migrated {moved} user(s) from "Marketing and IT" to "IT"')
                    # Now delete the legacy combined department
                    try:
                        name = mit_dept.name
                        mit_dept.delete()
                        self.stdout.write(f'Deleted legacy department: {name}')
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Could not delete legacy department: {e}'))
            
            # Optionally skip demo user creation in production environments
            skip_demo = os.environ.get('SKIP_DEMO_USERS') == '1' or os.environ.get('DEMO_USERS_ENABLED') == '0'
            if skip_demo:
                self.stdout.write('Environment requests skipping demo users (Ato, George, Augustine).')
            # Check if Ato exists (approver for IT)
            ato = (
                CustomUser.objects.filter(username='ato_manager').first()
                or CustomUser.objects.filter(first_name__icontains='Ato', role='manager').first()
            )
            if skip_demo:
                ato = ato  # no creation; only potential normalization/update below
            if ato:
                # Ensure department is set to IT
                if it_dept and getattr(ato, 'department', None) != it_dept:
                    CustomUser.objects.filter(pk=ato.pk).update(department=it_dept)
                self.stdout.write(f'Found approver: {ato.get_full_name()}')
            else:
                if skip_demo:
                    ato = None
                
                # Create Ato as a manager in IT
                if not skip_demo:
                    ato = CustomUser.objects.create_user(
                        username='ato_manager',
                        email='ato@company.com',
                        first_name='Ato',
                        last_name='Manager',
                        employee_id='EMP001',
                        role='manager',
                        department=it_dept,
                        is_demo=True
                    )
                    ato.set_password('password123')
                    ato.save()
                    self.stdout.write(f'Created approver: {ato.get_full_name()}')

            # Normalize seeded last names so role labels aren't part of the name
            for user in [u for u in [ato] if u]:
                if user.last_name in ['Manager', 'Staff']:
                    CustomUser.objects.filter(pk=user.pk).update(last_name='')
                    self.stdout.write(f"Normalized name for {user.username}: removed role word from last_name")
            
            # Check if George exists and assign to IT with Ato as manager
            george = (
                CustomUser.objects.filter(username='george_staff').first()
                or CustomUser.objects.filter(first_name__icontains='George').first()
            )
            if george:
                updates = {}
                if it_dept:
                    updates['department'] = it_dept
                if ato:
                    updates['manager'] = ato
                if not getattr(george, 'role', None):
                    updates['role'] = 'staff'
                if updates:
                    CustomUser.objects.filter(pk=george.pk).update(**updates)
                self.stdout.write('Updated George: assigned to IT with Ato as approver')
                if george.last_name in ['Manager', 'Staff']:
                    CustomUser.objects.filter(pk=george.pk).update(last_name='')
                    self.stdout.write('Normalized name for George: removed role word from last_name')
            else:
                # Create George
                if not skip_demo:
                    george = CustomUser.objects.create_user(
                        username='george_staff',
                        email='george@company.com',
                        first_name='George',
                        last_name='',
                        employee_id='EMP002',
                        role='staff',
                        department=it_dept,
                        manager=ato,
                        is_demo=True
                    )
                    george.set_password('password123')
                    george.save()
                    self.stdout.write('Created George: assigned to IT with Ato as approver')
            
            # Check if Augustine exists and assign to IT with Ato as manager
            augustine = (
                CustomUser.objects.filter(username='augustine_staff').first()
                or CustomUser.objects.filter(first_name__icontains='Augustine').first()
            )
            if augustine:
                updates = {}
                if it_dept:
                    updates['department'] = it_dept
                if ato:
                    updates['manager'] = ato
                if not getattr(augustine, 'role', None):
                    updates['role'] = 'staff'
                if updates:
                    CustomUser.objects.filter(pk=augustine.pk).update(**updates)
                self.stdout.write('Updated Augustine: assigned to IT with Ato as approver')
                if augustine.last_name in ['Manager', 'Staff']:
                    CustomUser.objects.filter(pk=augustine.pk).update(last_name='')
                    self.stdout.write('Normalized name for Augustine: removed role word from last_name')
            else:
                # Create Augustine
                if not skip_demo:
                    augustine = CustomUser.objects.create_user(
                        username='augustine_staff',
                        email='augustine@company.com',
                        first_name='Augustine',
                        last_name='',
                        employee_id='EMP003',
                        role='staff',
                        department=it_dept,
                        manager=ato,
                        is_demo=True
                    )
                    augustine.set_password('password123')
                    augustine.save()
                    self.stdout.write('Created Augustine: assigned to IT with Ato as approver')
            
            # Create HR user if not exists (unless skipped)
            if skip_hr:
                self.stdout.write('Skipping HR user creation due to --skip-hr flag.')
            else:
                hr_user = (
                    CustomUser.objects.filter(username='hr_admin').first()
                    or CustomUser.objects.filter(role='hr').first()
                )
                if hr_user:
                    self.stdout.write(f'HR user already exists: {hr_user.get_full_name()}')
                else:
                    hr_user = CustomUser.objects.create_user(
                        username='hr_admin',
                        email='hr@company.com',
                        first_name='HR',
                        last_name='Administrator',
                        employee_id='HR001',
                        role='hr',
                        department=created_departments.get('Client Service')  # Assign HR to Client Service
                    )
                    hr_user.set_password('password123')
                    hr_user.save()
                    self.stdout.write(f'Created HR user: {hr_user.get_full_name()}')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created departments and staff assignments!')
        )
        if not skip_demo:
            self.stdout.write('\nLogin credentials created:')
            self.stdout.write('HR Admin: username="hr_admin", password="password123"')
            self.stdout.write('Ato (Manager): username="ato_manager", password="password123"')
            self.stdout.write('George (Staff): username="george_staff", password="password123"')
            self.stdout.write('Augustine (Staff): username="augustine_staff", password="password123"')
        else:
            self.stdout.write('Demo user credential output suppressed (skip_demo active).')