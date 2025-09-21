from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Department
from leaves.models import LeaveType, LeaveBalance
from django.utils import timezone


class Command(BaseCommand):
    help = "Seed demo departments, users, and leave types for local testing"

    def handle(self, *args, **options):
        User = get_user_model()

        # Create Departments
        dept_names = [
            ("Engineering", "Builds the product"),
            ("Human Resources", "Manages people and policies"),
            ("Operations", "Keeps the lights on"),
        ]
        departments = {}
        for name, desc in dept_names:
            dept, created = Department.objects.get_or_create(name=name, defaults={"description": desc})
            departments[name] = dept
            self.stdout.write(self.style.SUCCESS(f"Department: {name} ({'created' if created else 'exists'})"))

        # Create Leave Types
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
            self.stdout.write(self.style.SUCCESS(f"LeaveType: {name} ({'created' if created else 'exists'})"))

        # Create Users
        users = [
            {
                "email": "john.doe@company.com",
                "username": "john.doe@company.com",
                "first_name": "John",
                "last_name": "Doe",
                "employee_id": "EMP001",
                "role": "staff",
                "department": departments.get("Engineering"),
                "password": "password123",
            },
            {
                "email": "manager@company.com",
                "username": "manager@company.com",
                "first_name": "Mary",
                "last_name": "Manager",
                "employee_id": "MGR001",
                "role": "manager",
                "department": departments.get("Engineering"),
                "password": "password123",
            },
            {
                "email": "hr@company.com",
                "username": "hr@company.com",
                "first_name": "Hank",
                "last_name": "HR",
                "employee_id": "HR001",
                "role": "hr",
                "department": departments.get("Human Resources"),
                "password": "password123",
            },
            {
                "email": "admin@company.com",
                "username": "admin@company.com",
                "first_name": "Alice",
                "last_name": "Admin",
                "employee_id": "ADM001",
                "role": "admin",
                "department": departments.get("Operations"),
                "password": "password123",
                "is_superuser": True,
                "is_staff": True,
            },
        ]

        for u in users:
            email = u["email"]
            password = u["password"]
            # fields to set/update on the user (excluding password)
            update_fields = {k: v for k, v in u.items() if k not in ["email", "password"]}

            user, created = User.objects.get_or_create(email=email, defaults=update_fields)

            # If the user already existed, update their profile fields to match demo data
            if not created:
                for field, value in update_fields.items():
                    setattr(user, field, value)

            # Always set/reset password so demo logins are predictable in dev
            user.set_password(password)
            user.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"User: {email} ({'created' if created else 'updated'}) — password reset"
                )
            )

        # Ensure leave balances exist for the current year for each user and leave type
        current_year = timezone.now().year
        default_entitlements = {
            'Annual Leave': 25,
            'Sick Leave': 14,
            'Maternity Leave': 90,
        }

        all_users = User.objects.all()
        all_types = LeaveType.objects.filter(is_active=True)
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

        self.stdout.write(self.style.SUCCESS("Demo data seeding complete."))
