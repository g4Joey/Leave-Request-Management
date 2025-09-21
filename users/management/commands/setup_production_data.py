from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
import os

# Seed models
from leaves.models import LeaveType, LeaveBalance


class Command(BaseCommand):
    help = "Idempotent setup for production data: ensure a superuser exists if env vars are provided."

    def handle(self, *args, **options):
        User = get_user_model()

        # Read optional superuser seed values from environment
        su_username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        su_email = os.getenv("DJANGO_SUPERUSER_EMAIL")
        su_password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
        su_employee_id = os.getenv("DJANGO_SUPERUSER_EMPLOYEE_ID", "ADMIN001")
        su_first_name = os.getenv("DJANGO_SUPERUSER_FIRST_NAME", "System")
        su_last_name = os.getenv("DJANGO_SUPERUSER_LAST_NAME", "Admin")

        if su_username and su_password:
            # Minimal defaults compatible with AbstractUser
            defaults = {
                "email": su_email or "",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "first_name": su_first_name,
                "last_name": su_last_name,
            }

            user, created = User.objects.get_or_create(
                username=su_username,
                defaults=defaults,
            )
            if created:
                user.set_password(su_password)
                # Optionally set custom fields if they exist
                if hasattr(user, "employee_id"):
                    setattr(user, "employee_id", su_employee_id)
                if hasattr(user, "role"):
                    setattr(user, "role", "admin")
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created superuser '{su_username}'"))
            else:
                # Ensure the flags and required fields are correct even if user already existed
                update_fields = []
                if not user.is_staff:
                    user.is_staff = True
                    update_fields.append("is_staff")
                if not user.is_superuser:
                    user.is_superuser = True
                    update_fields.append("is_superuser")
                if not getattr(user, "is_active", True):
                    user.is_active = True
                    update_fields.append("is_active")
                # Backfill required fields if missing
                if hasattr(user, "employee_id") and not getattr(user, "employee_id", None):
                    setattr(user, "employee_id", su_employee_id)
                    update_fields.append("employee_id")
                if hasattr(user, "role") and getattr(user, "role", None) != "admin":
                    setattr(user, "role", "admin")
                    update_fields.append("role")
                if update_fields:
                    user.save(update_fields=update_fields)
                self.stdout.write(self.style.WARNING(f"Superuser '{su_username}' already exists; ensured permissions."))
        else:
            self.stdout.write("No DJANGO_SUPERUSER_* env vars set; skipping superuser creation.")

        # Seed default Leave Types (idempotent)
        try:
            with transaction.atomic():
                self.stdout.write("Ensuring default leave types exist…")
                defaults = [
                    {
                        "name": "Annual Leave",
                        "description": "Annual leave (15 working days per year)",
                        "max_days_per_request": 15,
                        "requires_medical_certificate": False,
                        "is_active": True,
                    },
                    {
                        "name": "Maternity Leave",
                        "description": "Maternity leave (12 weeks paid)",
                        # 12 weeks ≈ 84 calendar days; adjust per policy later
                        "max_days_per_request": 84,
                        "requires_medical_certificate": False,
                        "is_active": True,
                    },
                    {
                        "name": "Sick Leave",
                        "description": "Sick leave",
                        "max_days_per_request": 10,
                        "requires_medical_certificate": True,
                        "is_active": True,
                    },
                ]

                type_map = {}
                for data in defaults:
                    obj, created = LeaveType.objects.get_or_create(
                        name=data["name"], defaults=data
                    )
                    type_map[data["name"]] = obj
                    if created:
                        self.stdout.write(self.style.SUCCESS(f"Created LeaveType: {obj.name}"))

                # Seed per-user Leave Balances for current year if missing
                current_year = timezone.now().year
                self.stdout.write(f"Ensuring leave balances exist for year {current_year}…")

                # Default entitlements per type (can be adjusted later via admin)
                entitlements = {
                    "Annual Leave": 15,
                    "Maternity Leave": 84,
                    "Sick Leave": 10,
                }

                for user in User.objects.filter(is_active=True):
                    for lt_name, entitlement in entitlements.items():
                        lt = type_map.get(lt_name)
                        if not lt:
                            continue
                        lb, created = LeaveBalance.objects.get_or_create(
                            employee=user,
                            leave_type=lt,
                            year=current_year,
                            defaults={
                                "entitled_days": entitlement,
                                "used_days": 0,
                                "pending_days": 0,
                            },
                        )
                        if created:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Created LeaveBalance for {user.email or user.username} - {lt.name} ({current_year})"
                                )
                            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error seeding leave types/balances: {e}"))

        # Optional: add more seed logic here (departments, initial roles, etc.)
        self.stdout.write(self.style.SUCCESS("setup_production_data completed."))