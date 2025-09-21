from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Department
from leaves.models import LeaveType, LeaveBalance
from django.db import transaction
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = 'Set up production data (departments, leave types, admin user)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-email',
            type=str,
            default='admin@company.com',
            help='Admin user email'
        )
        parser.add_argument(
            '--admin-password',
            type=str,
            default='Admin123!',
            help='Admin user password'
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write("🚀 Setting up production data...")
            
            # Create departments
            departments_data = [
                {'name': 'Human Resources', 'description': 'HR Department'},
                {'name': 'Engineering', 'description': 'Software Development'},
                {'name': 'Marketing', 'description': 'Marketing and Sales'},
                {'name': 'Finance', 'description': 'Finance and Accounting'},
                {'name': 'Operations', 'description': 'Operations and Support'},
            ]
            
            for dept_data in departments_data:
                dept, created = Department.objects.get_or_create(
                    name=dept_data['name'],
                    defaults=dept_data
                )
                status = "✅ Created" if created else "📋 Already exists"
                self.stdout.write(f"   {status}: Department '{dept.name}'")

            # Create leave types
            leave_types_data = [
                {
                    'name': 'Annual Leave',
                    'description': 'Yearly vacation days',
                    'max_days_per_request': 30,
                    'requires_medical_certificate': False,
                    'is_active': True
                },
                {
                    'name': 'Sick Leave',
                    'description': 'Medical leave',
                    'max_days_per_request': 14,
                    'requires_medical_certificate': True,
                    'is_active': True
                },
                {
                    'name': 'Maternity Leave',
                    'description': 'Maternity leave for new mothers',
                    'max_days_per_request': 90,
                    'requires_medical_certificate': False,
                    'is_active': True
                },
                {
                    'name': 'Personal Leave',
                    'description': 'Personal time off',
                    'max_days_per_request': 5,
                    'requires_medical_certificate': False,
                    'is_active': True
                }
            ]
            
            for leave_data in leave_types_data:
                leave_type, created = LeaveType.objects.get_or_create(
                    name=leave_data['name'],
                    defaults=leave_data
                )
                status = "✅ Created" if created else "📋 Already exists"
                self.stdout.write(f"   {status}: Leave type '{leave_type.name}'")

            # Create admin user
            admin_email = options['admin_email']
            admin_password = options['admin_password']
            hr_dept = Department.objects.filter(name='Human Resources').first()
            
            admin_user, created = User.objects.get_or_create(
                email=admin_email,
                defaults={
                    'username': admin_email,
                    'first_name': 'System',
                    'last_name': 'Administrator',
                    'employee_id': 'ADMIN001',
                    'role': 'admin',
                    'department': hr_dept,
                    'is_staff': True,
                    'is_superuser': True,
                    'is_active': True,
                }
            )
            
            if created:
                admin_user.set_password(admin_password)
                admin_user.save()
                status = f"✅ Created admin user: {admin_email}"
            else:
                # Update password for existing admin
                admin_user.set_password(admin_password)
                admin_user.is_staff = True
                admin_user.is_superuser = True
                admin_user.save()
                status = f"🔄 Updated admin user: {admin_email}"
            
            self.stdout.write(f"   {status}")
            
            # Create demo employee for testing
            demo_user, created = User.objects.get_or_create(
                email='john.doe@company.com',
                defaults={
                    'username': 'john.doe@company.com',
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'employee_id': 'EMP001',
                    'role': 'staff',
                    'department': Department.objects.filter(name='Engineering').first(),
                    'is_active': True,
                }
            )
            
            if created:
                demo_user.set_password('password123')
                demo_user.save()
                status = "✅ Created demo employee: john.doe@company.com"
            else:
                demo_user.set_password('password123')
                demo_user.save()
                status = "🔄 Updated demo employee: john.doe@company.com"
            
            self.stdout.write(f"   {status}")

            # Create leave balances for all users
            current_year = timezone.now().year
            default_entitlements = {
                'Annual Leave': 25,
                'Sick Leave': 14,
                'Maternity Leave': 90,
                'Personal Leave': 5,
            }

            all_users = User.objects.filter(is_active=True)
            all_types = LeaveType.objects.filter(is_active=True)
            
            balances_created = 0
            for user in all_users:
                for leave_type in all_types:
                    entitled = default_entitlements.get(leave_type.name, 0)
                    balance, created = LeaveBalance.objects.get_or_create(
                        employee=user,
                        leave_type=leave_type,
                        year=current_year,
                        defaults={
                            'entitled_days': entitled,
                            'used_days': 0,
                            'pending_days': 0,
                        }
                    )
                    if created:
                        balances_created += 1
                    elif balance.entitled_days == 0 and entitled:
                        balance.entitled_days = entitled
                        balance.save()

            self.stdout.write(f"   ✅ Created/updated {balances_created} leave balance records")

            self.stdout.write(
                self.style.SUCCESS('\n🎉 Production setup completed successfully!')
            )
            self.stdout.write(
                self.style.WARNING(f"\n🔐 Admin credentials:")
            )
            self.stdout.write(f"   Email: {admin_email}")
            self.stdout.write(f"   Password: {admin_password}")
            self.stdout.write(
                self.style.WARNING(f"\n👤 Demo user credentials:")
            )
            self.stdout.write(f"   Email: john.doe@company.com")
            self.stdout.write(f"   Password: password123")
            self.stdout.write(
                self.style.SUCCESS(f"\n🌐 Your app will be available at:")
            )
            self.stdout.write(f"   https://takeabreak-app-38abv.ondigitalocean.app")