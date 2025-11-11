"""
Management command to set up a fresh database with initial data
This should be run after creating a new database
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from django.contrib.auth import get_user_model
from leaves.models import LeaveType, LeaveBalance
from users.models import Affiliate, Department
import json
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Set up a fresh database with initial data, users, and leave balances'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== SETTING UP FRESH DATABASE ==='))
        
        # 1. Run migrations first
        self.stdout.write('Running migrations...')
        call_command('migrate', verbosity=0)
        self.stdout.write(self.style.SUCCESS('Migrations completed'))
        
        # 2. Create leave types
        self.stdout.write('Creating leave types...')
        leave_types_data = [
            {'name': 'Annual Leave', 'description': 'Annual vacation leave', 'is_active': True},
            {'name': 'Sick Leave', 'description': 'Medical leave', 'is_active': True},
            {'name': 'Casual Leave', 'description': 'Short-term casual leave', 'is_active': True},
            {'name': 'Maternity Leave', 'description': 'Maternity leave', 'is_active': True},
            {'name': 'Paternity Leave', 'description': 'Paternity leave', 'is_active': True},
            {'name': 'Compassionate Leave', 'description': 'Bereavement/compassionate leave', 'is_active': True},
        ]
        
        for lt_data in leave_types_data:
            leave_type, created = LeaveType.objects.get_or_create(
                name=lt_data['name'],
                defaults=lt_data
            )
            if created:
                self.stdout.write(f'  Created leave type: {leave_type.name}')
            else:
                self.stdout.write(f'  Leave type already exists: {leave_type.name}')
        
        # 3. Create or load users
        self.stdout.write('Setting up users...')
        
        # Check if we have a seed file
        seed_file = os.path.join('local', 'seed_users.json')
        if os.path.exists(seed_file):
            self.stdout.write('Loading users from seed file...')
            with open(seed_file, 'r') as f:
                users_data = json.load(f)
            
            # Preload affiliate and department maps for efficient resolution
            affiliate_map = {a.name.lower(): a for a in Affiliate.objects.all()}
            dept_map = {d.name.lower(): d for d in Department.objects.all()}

            for user_data in users_data:
                if not isinstance(user_data, dict):
                    continue
                username = user_data.get('username') or user_data.get('email')
                if not username:
                    continue
                raw_affiliate = (user_data.get('affiliate') or '').strip()
                affiliate_obj = None
                if raw_affiliate:
                    key = raw_affiliate.lower()
                    affiliate_obj = affiliate_map.get(key)
                    if not affiliate_obj:
                        affiliate_obj = Affiliate.objects.create(name=raw_affiliate)
                        affiliate_map[key] = affiliate_obj
                        self.stdout.write(f"  Created affiliate: {raw_affiliate}")

                # Department only meaningful for Merban Capital (or if explicitly provided); ensure affiliate link
                dept_name = (user_data.get('department') or '').strip()
                dept_obj = None
                if dept_name:
                    dkey = dept_name.lower()
                    dept_obj = dept_map.get(dkey)
                    if not dept_obj:
                        dept_obj = Department.objects.create(name=dept_name, affiliate=affiliate_obj if affiliate_obj else None)
                        dept_map[dkey] = dept_obj
                        self.stdout.write(f"  Created department: {dept_name}")
                    elif affiliate_obj and dept_obj.affiliate_id != affiliate_obj.id:
                        dept_obj.affiliate = affiliate_obj
                        dept_obj.save(update_fields=['affiliate'])
                        self.stdout.write(f"  Linked existing department '{dept_name}' to affiliate '{affiliate_obj.name}'")

                role = user_data.get('role', 'junior_staff')
                employee_id = user_data.get('employee_id') or f"AUTO_{username}".upper()
                first_name = user_data.get('first_name', '')
                last_name = user_data.get('last_name', '')
                email = user_data.get('email', username)
                manager_username = user_data.get('manager')
                manager_obj = None
                if manager_username:
                    manager_obj = User.objects.filter(username=manager_username).first()

                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'first_name': first_name,
                        'last_name': last_name,
                        'role': role,
                        'employee_id': employee_id,
                        'affiliate': affiliate_obj,
                        'department': dept_obj,
                        'manager': manager_obj,
                        'is_active': True,
                        'is_active_employee': True,
                    }
                )
                if created:
                    pwd = user_data.get('password')
                    if pwd:
                        user.set_password(pwd)
                    else:
                        user.set_unusable_password()
                    user.save()
                    self.stdout.write(f"  Created user: {username} (role={role}, affiliate={getattr(affiliate_obj,'name',None)})")
                else:
                    # Update affiliate/department if newly provided (do not change password)
                    updates = {}
                    for field, val in [
                        ('affiliate', affiliate_obj),
                        ('department', dept_obj),
                        ('manager', manager_obj),
                        ('role', role),
                        ('first_name', first_name),
                        ('last_name', last_name),
                        ('email', email),
                    ]:
                        if val is not None and getattr(user, field) != val:
                            updates[field] = val
                    if updates:
                        User.objects.filter(pk=user.pk).update(**updates)
                        self.stdout.write(f"  Updated user: {username} fields: {', '.join(updates.keys())}")
                    else:
                        self.stdout.write(f"  User already exists (no changes): {username}")
        else:
            # Create basic users if no seed file
            self.stdout.write('No seed file found, creating basic users...')
            
            # Create admin user
            admin_user, created = User.objects.get_or_create(
                username='admin@company.com',
                defaults={
                    'email': 'admin@company.com',
                    'first_name': 'System',
                    'last_name': 'Admin',
                    'role': 'manager',
                    'is_active': True,
                    'is_active_employee': True,
                    'is_superuser': True,
                    'is_staff': True,
                }
            )
            if created:
                admin_user.set_password('admin123')
                admin_user.save()
                self.stdout.write(self.style.SUCCESS('Created admin user: admin@company.com / admin123'))
            
            # Create test users matching the existing database usernames
            test_users = [
                {'username': 'gsafo', 'email': 'gsafo@umbcapital.com', 'first_name': 'George', 'last_name': 'Safo', 'role': 'senior_staff'},
                {'username': 'aakorfu', 'email': 'aakorfu@umbcapital.com', 'first_name': 'Augustine', 'last_name': 'Korfu', 'role': 'junior_staff'},
                {'username': 'jmankoe', 'email': 'jmankoe@umbcapital.com', 'first_name': 'Joshua', 'last_name': 'Mankoe', 'role': 'manager'},
                {'username': 'hr_admin', 'email': 'hr@umbcapital.com', 'first_name': 'HR', 'last_name': 'Admin', 'role': 'hr'},
            ]
            
            for user_data in test_users:
                user, created = User.objects.get_or_create(
                    username=user_data['username'],
                    defaults={
                        'email': user_data['email'],
                        'first_name': user_data['first_name'],
                        'last_name': user_data['last_name'],
                        'role': user_data['role'],
                        'is_active': True,
                        'is_active_employee': True,
                        'is_superuser': user_data['role'] in ['manager', 'hr'],
                        'is_staff': user_data['role'] in ['manager', 'hr'],
                    }
                )
                if created:
                    user.set_password('password123')
                    user.save()
                    self.stdout.write(f'  Created user: {user_data["username"]} ({user_data["email"]}) / password123')
        
        # 4. Set up leave balances for current year
        self.stdout.write('Setting up leave balances...')
        current_year = timezone.now().year
        
        active_employees = User.objects.filter(is_active=True, is_active_employee=True)
        active_leave_types = LeaveType.objects.filter(is_active=True)
        
        self.stdout.write(f'Found {active_employees.count()} active employees')
        self.stdout.write(f'Found {active_leave_types.count()} active leave types')
        
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
        for employee in active_employees:
            for leave_type in active_leave_types:
                days = default_entitlements.get(leave_type.name, 0)
                if days > 0:
                    balance, was_created = LeaveBalance.objects.get_or_create(
                        employee=employee,
                        leave_type=leave_type,
                        year=current_year,
                        defaults={'entitled_days': days, 'used_days': 0, 'pending_days': 0}
                    )
                    if was_created:
                        created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {created_count} leave balance records'))
        
        # 5. Final summary
        self.stdout.write(self.style.SUCCESS('=== DATABASE SETUP COMPLETE ==='))
        self.stdout.write(f'Users: {User.objects.count()}')
        self.stdout.write(f'Active employees: {active_employees.count()}')
        self.stdout.write(f'Leave types: {LeaveType.objects.count()}')
        self.stdout.write(f'Leave balances for {current_year}: {LeaveBalance.objects.filter(year=current_year).count()}')
        
        # Show managers
        managers = User.objects.filter(role='manager')
        self.stdout.write(f'Managers: {managers.count()}')
        for manager in managers:
            self.stdout.write(f'  - {manager.username} ({manager.get_full_name()})')