from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import Department, CustomUser


class Command(BaseCommand):
    help = 'Create departments and assign staff with approvers'

    def handle(self, *args, **options):
        self.stdout.write('Creating departments and staff assignments...')
        
        with transaction.atomic():
            # Create departments
            departments_data = [
                ('Accounts & Compliance', 'Financial accounts and regulatory compliance'),
                ('IHL', 'Investment and Holdings Limited'),
                ('Stockbrokers', 'Stock brokerage services'),
                ('SDSL', 'Securities Dealing Services Limited'),
                ('Client Service', 'Customer service and support'),
                ('Pensions', 'Pension fund management'),
                ('Government Securities', 'Government securities trading'),
                ('Marketing and IT', 'Marketing, communications and Information Technology services'),
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
            
            # Get Marketing and IT department for George and Augustine
            mit_dept = created_departments.get('Marketing and IT')
            
            # Check if Ato exists (approver for IT)
            ato = (
                CustomUser.objects.filter(username='ato_manager').first()
                or CustomUser.objects.filter(first_name__icontains='Ato', role='manager').first()
            )
            if ato:
                # Ensure department is set
                if mit_dept and getattr(ato, 'department', None) != mit_dept:
                    CustomUser.objects.filter(pk=ato.pk).update(department=mit_dept)
                self.stdout.write(f'Found approver: {ato.get_full_name()}')
            else:
                # Create Ato as a manager in Marketing and IT
                ato = CustomUser.objects.create_user(
                    username='ato_manager',
                    email='ato@company.com',
                    first_name='Ato',
                    last_name='Manager',
                    employee_id='EMP001',
                    role='manager',
                    department=mit_dept
                )
                ato.set_password('password123')
                ato.save()
                self.stdout.write(f'Created approver: {ato.get_full_name()}')
            
            # Check if George exists and assign to IT with Ato as manager
            george = (
                CustomUser.objects.filter(username='george_staff').first()
                or CustomUser.objects.filter(first_name__icontains='George').first()
            )
            if george:
                updates = {}
                if mit_dept:
                    updates['department'] = mit_dept
                if ato:
                    updates['manager'] = ato
                if not getattr(george, 'role', None):
                    updates['role'] = 'staff'
                if updates:
                    CustomUser.objects.filter(pk=george.pk).update(**updates)
                self.stdout.write('Updated George: assigned to Marketing and IT with Ato as approver')
            else:
                # Create George
                george = CustomUser.objects.create_user(
                    username='george_staff',
                    email='george@company.com',
                    first_name='George',
                    last_name='Staff',
                    employee_id='EMP002',
                    role='staff',
                    department=mit_dept,
                    manager=ato
                )
                george.set_password('password123')
                george.save()
                self.stdout.write('Created George: assigned to Marketing and IT with Ato as approver')
            
            # Check if Augustine exists and assign to IT with Ato as manager
            augustine = (
                CustomUser.objects.filter(username='augustine_staff').first()
                or CustomUser.objects.filter(first_name__icontains='Augustine').first()
            )
            if augustine:
                updates = {}
                if mit_dept:
                    updates['department'] = mit_dept
                if ato:
                    updates['manager'] = ato
                if not getattr(augustine, 'role', None):
                    updates['role'] = 'staff'
                if updates:
                    CustomUser.objects.filter(pk=augustine.pk).update(**updates)
                self.stdout.write('Updated Augustine: assigned to Marketing and IT with Ato as approver')
            else:
                # Create Augustine
                augustine = CustomUser.objects.create_user(
                    username='augustine_staff',
                    email='augustine@company.com',
                    first_name='Augustine',
                    last_name='Staff',
                    employee_id='EMP003',
                    role='staff',
                    department=mit_dept,
                    manager=ato
                )
                augustine.set_password('password123')
                augustine.save()
                self.stdout.write('Created Augustine: assigned to Marketing and IT with Ato as approver')
            
            # Create HR user if not exists
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
        self.stdout.write('\nLogin credentials created:')
        self.stdout.write('HR Admin: username="hr_admin", password="password123"')
        self.stdout.write('Ato (Manager): username="ato_manager", password="password123"')
        self.stdout.write('George (Staff): username="george_staff", password="password123"')
        self.stdout.write('Augustine (Staff): username="augustine_staff", password="password123"')