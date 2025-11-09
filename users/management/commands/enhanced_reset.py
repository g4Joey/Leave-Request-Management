"""
Enhanced production reset command that uses the same balance creation logic as seed_demo_data
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from users.models import Department, Affiliate
from leaves.models import LeaveType, LeaveBalance, LeaveRequest
from notifications.models import Notification
from django.utils import timezone
import os

User = get_user_model()


class Command(BaseCommand):
    help = 'Enhanced production reset with proper balance creation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true', 
            help='Confirm the reset operation'
        )

    def handle(self, *args, **options):
        if not options.get('confirm'):
            self.stdout.write(
                self.style.WARNING(
                    'This will reset ALL user data, leave requests, balances, and notifications.\n'
                    'Run with --confirm to proceed.'
                )
            )
            return

        self.stdout.write('Starting enhanced production reset...')
        
        with transaction.atomic():
            # 1. Delete all user-related data (preserve superusers)
            superuser_ids = list(User.objects.filter(is_superuser=True).values_list('id', flat=True))
            
            # Delete leave requests and balances
            deleted_requests = LeaveRequest.objects.exclude(employee_id__in=superuser_ids).count()
            LeaveRequest.objects.exclude(employee_id__in=superuser_ids).delete()
            
            deleted_balances = LeaveBalance.objects.exclude(employee_id__in=superuser_ids).count()
            LeaveBalance.objects.exclude(employee_id__in=superuser_ids).delete()
            
            # Delete notifications
            deleted_notifications = Notification.objects.exclude(recipient_id__in=superuser_ids).count() 
            Notification.objects.exclude(recipient_id__in=superuser_ids).delete()
            
            # Delete regular users (preserve superusers)
            deleted_users = User.objects.exclude(id__in=superuser_ids).count()
            User.objects.exclude(id__in=superuser_ids).delete()
            
            self.stdout.write(f'Deleted {deleted_users} users, {deleted_requests} requests, {deleted_balances} balances, {deleted_notifications} notifications')
            
            # 3. Clean up orphaned HOD assignments in departments
            Department.objects.exclude(hod_id__in=superuser_ids + [None]).update(hod=None)
            
            # 3. Now recreate the system using seed_demo_data logic
            # Ensure affiliates exist
            merban, _ = Affiliate.objects.get_or_create(
                name='MERBAN CAPITAL',
                defaults={'description': 'Merban Capital affiliate'}
            )
            sdsl, _ = Affiliate.objects.get_or_create(
                name='SDSL', 
                defaults={'description': 'SDSL affiliate'}
            )
            sbl, _ = Affiliate.objects.get_or_create(
                name='SBL',
                defaults={'description': 'SBL affiliate'}
            )
            
            # 4. Ensure canonical departments for Merban Capital
            dept_names = [
                ("Finance & Accounts", "Financial accounts and accounting services"),
                ("Government Securities", "Government securities trading"), 
                ("Pensions & Provident Fund", "Pension fund and provident fund management"),
                ("Private Wealth & Mutual Fund", "Private wealth management and mutual fund services"),
                ("HR & Admin", "Human resources and administrative services"),
                ("Client Service/Marketing", "Customer service and marketing"),
                ("Corporate Finance", "Corporate finance and advisory services"),
                ("IT", "Information Technology services"),
                ("Compliance", "Regulatory compliance and oversight"),
                ("Audit", "Internal and external audit services"),
            ]
            
            departments = {}
            for name, desc in dept_names:
                dept, created = Department.objects.get_or_create(
                    name=name, 
                    affiliate=merban,
                    defaults={"description": desc}
                )
                departments[name] = dept
                self.stdout.write(f"Department: {name} ({'created' if created else 'exists'})")
            
            # 5. Ensure leave types exist
            lt_names = [
                ("Annual Leave", "Paid annual leave", 30, False),
                ("Sick Leave", "Sick days", 14, True), 
                ("Maternity Leave", "Maternity leave", 90, False),
            ]
            for name, desc, max_days, requires_med in lt_names:
                lt, created = LeaveType.objects.get_or_create(
                    name=name, defaults={
                        "description": desc,
                        "max_days_per_request": max_days,
                        "requires_medical_certificate": requires_med
                    }
                )
                self.stdout.write(f"LeaveType: {name} ({'created' if created else 'exists'})")
            
            # 6. Create 9 demo users across affiliates with env overrides (no past requests recreated)

            def env(name: str, default: str) -> str:
                return os.getenv(name, default).strip()

            def username_from_email(email: str, fallback: str) -> str:
                return (email.split('@')[0] if '@' in email and email.split('@')[0] else fallback)

            # Defaults per your specification, can be overridden via environment variables
            merban_ceo_email = env('MERBAN_CEO_EMAIL', 'ceo@umbcapital.com')
            merban_ceo_first = env('MERBAN_CEO_FIRST', 'Benjamin')
            merban_ceo_last  = env('MERBAN_CEO_LAST',  'Ackah')

            # Updated default HR email per request (previously hr@merban.com)
            merban_hr_email = env('MERBAN_HR_EMAIL', 'hradmin@umbcapital.com')
            merban_hr_first = env('MERBAN_HR_FIRST', 'Nana Ama')
            merban_hr_last  = env('MERBAN_HR_LAST',  'Daatano')

            merban_mgr_email = env('MERBAN_MANAGER_EMAIL', 'jmankoe@umbcapital.com')
            merban_mgr_first = env('MERBAN_MANAGER_FIRST', 'Joseph')
            merban_mgr_last  = env('MERBAN_MANAGER_LAST',  'Mankoe')

            merban_staff_email = env('MERBAN_STAFF_EMAIL', 'aakorfu@umbcapital.com')
            merban_staff_first = env('MERBAN_STAFF_FIRST', 'Augustine')
            merban_staff_last  = env('MERBAN_STAFF_LAST',  'Akorfu')

            merban_senior_email = env('MERBAN_SENIOR_STAFF_EMAIL', 'gsafo@umbcapital.com')
            merban_senior_first = env('MERBAN_SENIOR_STAFF_FIRST', 'George')
            merban_senior_last  = env('MERBAN_SENIOR_STAFF_LAST',  'Safo')

            sdsl_ceo_email = env('SDSL_CEO_EMAIL', 'sdslceo@umbcapital.com')
            sdsl_ceo_first = env('SDSL_CEO_FIRST', 'Kofi')
            sdsl_ceo_last  = env('SDSL_CEO_LAST',  'Ameyaw')

            sdsl_staff_email = env('SDSL_STAFF_EMAIL', 'asanunu@umbcapital.com')
            sdsl_staff_first = env('SDSL_STAFF_FIRST', 'Augustine')
            sdsl_staff_last  = env('SDSL_STAFF_LAST',  'Sanunu')

            sbl_ceo_email = env('SBL_CEO_EMAIL', 'sblceo@umbcapital.com')
            sbl_ceo_first = env('SBL_CEO_FIRST', 'Winslow')
            sbl_ceo_last  = env('SBL_CEO_LAST',  'Sackey')

            sbl_staff_email = env('SBL_STAFF_EMAIL', 'staff@sbl.com')  # override with real email via env
            sbl_staff_first = env('SBL_STAFF_FIRST', 'Eric')
            sbl_staff_last  = env('SBL_STAFF_LAST',  'Nartey')

            demo_users = [
                # Merban Capital (CEO, HR, Manager, Junior Staff, Senior Staff)
                {'email': merban_ceo_email,    'username': username_from_email(merban_ceo_email,    'merban_ceo'),  'first_name': merban_ceo_first,    'last_name': merban_ceo_last,    'role': 'ceo',          'affiliate': merban, 'department': None,                           'employee_id': 'DEMO001'},
                {'email': merban_hr_email,     'username': username_from_email(merban_hr_email,     'merban_hr'),   'first_name': merban_hr_first,     'last_name': merban_hr_last,     'role': 'hr',           'affiliate': merban, 'department': departments.get('HR & Admin'), 'employee_id': 'DEMO002'},
                {'email': merban_mgr_email,    'username': username_from_email(merban_mgr_email,    'merban_mgr'),  'first_name': merban_mgr_first,    'last_name': merban_mgr_last,    'role': 'manager',      'affiliate': merban, 'department': departments.get('IT'),         'employee_id': 'DEMO003'},
                {'email': merban_staff_email,  'username': username_from_email(merban_staff_email,  'merban_staff'),'first_name': merban_staff_first,  'last_name': merban_staff_last,  'role': 'junior_staff', 'affiliate': merban, 'department': departments.get('IT'),         'employee_id': 'DEMO004'},
                {'email': merban_senior_email, 'username': username_from_email(merban_senior_email, 'merban_snr'),  'first_name': merban_senior_first, 'last_name': merban_senior_last, 'role': 'senior_staff', 'affiliate': merban, 'department': departments.get('IT'),         'employee_id': 'DEMO009'},
                # SDSL (no departments/managers)
                {'email': sdsl_ceo_email,      'username': username_from_email(sdsl_ceo_email,      'sdsl_ceo'),    'first_name': sdsl_ceo_first,      'last_name': sdsl_ceo_last,      'role': 'ceo',          'affiliate': sdsl,   'department': None,                           'employee_id': 'DEMO005'},
                {'email': sdsl_staff_email,    'username': username_from_email(sdsl_staff_email,    'sdsl_staff'),  'first_name': sdsl_staff_first,    'last_name': sdsl_staff_last,    'role': 'senior_staff', 'affiliate': sdsl,   'department': None,                           'employee_id': 'DEMO006'},
                # SBL (no departments/managers)
                {'email': sbl_ceo_email,       'username': username_from_email(sbl_ceo_email,       'sbl_ceo'),     'first_name': sbl_ceo_first,       'last_name': sbl_ceo_last,       'role': 'ceo',          'affiliate': sbl,    'department': None,                           'employee_id': 'DEMO007'},
                {'email': sbl_staff_email,     'username': username_from_email(sbl_staff_email,     'sbl_staff'),   'first_name': sbl_staff_first,     'last_name': sbl_staff_last,     'role': 'senior_staff', 'affiliate': sbl,    'department': None,                           'employee_id': 'DEMO008'},
            ]

            created_users = []
            for u in demo_users:
                user = User.objects.create_user(
                    username=u['username'],
                    email=u['email'],
                    first_name=u['first_name'],
                    last_name=u['last_name'],
                    employee_id=u['employee_id'],
                    password='ChangeMe123!',
                    role=u['role'],
                    department=u['department'],
                    affiliate=u['affiliate'],
                    is_staff=True if u['role'] in ['hr','manager','ceo','admin'] else False,
                    annual_leave_entitlement=25,
                    is_active_employee=True,
                    is_demo=True,
                )
                created_users.append(user)
                self.stdout.write(f"Created {u['role'].upper()}: {user.get_full_name()} <{user.email}>")
            
            # 7. Create leave balances for current demo users only; no past requests recreated
            current_year = timezone.now().year
            default_entitlements = {
                'Annual Leave': 25,
                'Sick Leave': 14, 
                'Maternity Leave': 90,
            }
            
            all_users = User.objects.filter(is_demo=True)
            all_types = LeaveType.objects.filter(is_active=True)
            balance_count = 0
            
            for user in all_users:
                for lt in all_types:
                    entitled = default_entitlements.get(lt.name, 0)
                    balance, b_created = LeaveBalance.objects.get_or_create(
                        employee=user,
                        leave_type=lt,
                        year=current_year,
                        defaults={
                            'entitled_days': entitled,
                            'used_days': 0,
                            'pending_days': 0,
                        }
                    )
                    if not b_created and balance.entitled_days == 0 and entitled:
                        balance.entitled_days = entitled
                        balance.save()
                    if b_created:
                        balance_count += 1
            
            self.stdout.write(f"Created {balance_count} leave balances for {all_users.count()} users")

            # 7b. Ensure platform superuser admin exists (not part of demo users)
            admin_email = os.getenv('PLATFORM_ADMIN_EMAIL', 'admin@umbcapital.com').strip()
            admin_username = os.getenv('PLATFORM_ADMIN_USERNAME', 'admin').strip()
            admin_password = os.getenv('PLATFORM_ADMIN_PASSWORD', os.getenv('ADMIN_PASSWORD', 'AdminChangeMe123!')).strip()

            if not User.objects.filter(email=admin_email).exists():
                # Avoid username collision
                base_username = admin_username
                suffix = 1
                while User.objects.filter(username=admin_username).exists():
                    admin_username = f"{base_username}{suffix}"
                    suffix += 1
                su = User.objects.create_superuser(
                    username=admin_username,
                    email=admin_email,
                    password=admin_password,
                    first_name='Platform',
                    last_name='Admin',
                    employee_id='SUPERADMIN',
                    role='admin',
                    is_demo=False,
                )
                self.stdout.write(self.style.SUCCESS(f"Created superuser: {su.username} <{admin_email}>"))
            else:
                self.stdout.write(f"Superuser {admin_email} already exists – leaving unchanged")
            
        # 8. Create marker file to confirm execution
        marker_path = '/tmp/enhanced_reset_executed.txt' if os.name != 'nt' else 'enhanced_reset_executed.txt'
        with open(marker_path, 'w') as f:
            f.write(f'Enhanced reset executed at {timezone.now()}\n')
            f.write(f'Reset users: {deleted_users}\n') 
            f.write(f'Created demo users: {len(created_users)}\n')
            f.write(f'Created balances: {balance_count}\n')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Enhanced production reset complete!\n'
                f'- Deleted {deleted_users} users, {deleted_requests} requests, {deleted_balances} balances\n'
                f'- Created {len(created_users)} demo users across affiliates\n'
                f'- Created {balance_count} leave balances\n'
                f'- All departments ready for fresh CSV imports\n'
                f'Marker file: {marker_path}'
            )
        )