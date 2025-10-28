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
            
            # 6. Create CEOs as individual entities
            ceo_assignments = [
                {
                    'email': 'ceo@umbcapital.com',
                    'username': 'benja_ceo',
                    'first_name': 'Benjamin',
                    'last_name': 'Ackah'
                },
                {
                    'email': 'sdslceo@umbcapital.com',
                    'username': 'kofi_ceo', 
                    'first_name': 'Kofi',
                    'last_name': 'Ameyaw'
                },
                {
                    'email': 'sblceo@umbcapital.com',
                    'username': 'winslow_ceo',
                    'first_name': 'Winslow',
                    'last_name': 'Sackey'
                }
            ]
            
            created_users = []
            for i, assignment in enumerate(ceo_assignments, 1):
                user = User.objects.create_user(
                    username=assignment['username'],
                    email=assignment['email'],
                    first_name=assignment['first_name'],
                    last_name=assignment['last_name'],
                    employee_id=f'CEO{i:03d}',  # Temporary until employee_id is removed
                    password='ChangeMe123!',
                    role='ceo',
                    department=None,  # CEOs are individual entities
                    is_staff=True,
                    annual_leave_entitlement=30,
                    is_active_employee=True
                )
                created_users.append(user)
                self.stdout.write(f"Created CEO: {user.get_full_name()} <{user.email}>")
            
            # 7. Create leave balances for all users (including CEOs) - using seed_demo_data logic
            current_year = timezone.now().year
            default_entitlements = {
                'Annual Leave': 25,
                'Sick Leave': 14, 
                'Maternity Leave': 90,
            }
            
            all_users = User.objects.all()
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
            
        # 8. Create marker file to confirm execution
        marker_path = '/tmp/enhanced_reset_executed.txt' if os.name != 'nt' else 'enhanced_reset_executed.txt'
        with open(marker_path, 'w') as f:
            f.write(f'Enhanced reset executed at {timezone.now()}\n')
            f.write(f'Reset users: {deleted_users}\n') 
            f.write(f'Created CEOs: {len(ceo_assignments)}\n')
            f.write(f'Created balances: {balance_count}\n')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Enhanced production reset complete!\n'
                f'- Deleted {deleted_users} users, {deleted_requests} requests, {deleted_balances} balances\n'
                f'- Created {len(ceo_assignments)} CEOs as individual entities\n'
                f'- Created {balance_count} leave balances\n'
                f'- All departments ready for fresh CSV imports\n'
                f'Marker file: {marker_path}'
            )
        )