from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
import os
import json

# Seed models
from leaves.models import LeaveType, LeaveBalance
from users.models import Department


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

        # Optionally seed departments and users from environment (idempotent and safe)
        try:
            self.stdout.write("Ensuring base Department records…")
            # Ensure IT department exists for requests
            it_dept, _ = Department.objects.get_or_create(name="IT", defaults={"description": "Information Technology"})
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error ensuring departments: {e}"))

        # Load seed users from env var JSON, file path, or optional local file
        seed_users_env = os.getenv("SEED_USERS")
        seed_users_file = os.getenv("SEED_USERS_FILE")
        local_seed_file = os.path.join(os.getcwd(), "local", "seed_users.json")

        users_payload = None
        if seed_users_env:
            users_payload = seed_users_env
        elif seed_users_file and os.path.exists(seed_users_file):
            with open(seed_users_file, "r", encoding="utf-8") as f:
                users_payload = f.read()
        elif os.path.exists(local_seed_file):
            with open(local_seed_file, "r", encoding="utf-8") as f:
                users_payload = f.read()

        if users_payload:
            try:
                users_to_seed = json.loads(users_payload)
                if not isinstance(users_to_seed, list):
                    raise ValueError("SEED_USERS must be a JSON array of user objects")

                self.stdout.write(f"Seeding {len(users_to_seed)} user(s) from SEED_USERS…")
                for idx, u in enumerate(users_to_seed, start=1):
                    # Expected fields with fallbacks
                    email = (u.get("email") or "").strip().lower()
                    username = u.get("username") or email or f"user{idx:03d}"
                    first_name = u.get("first_name") or ""
                    last_name = u.get("last_name") or ""
                    role = (u.get("role") or "staff").lower()
                    dept_name = u.get("department") or "IT"
                    password = u.get("password")
                    employee_id = u.get("employee_id")

                    # Ensure department
                    department = None
                    if dept_name:
                        department, _ = Department.objects.get_or_create(name=dept_name)

                    # Prepare defaults (ensure unique employee_id at creation to avoid duplicates)
                    emp_id_default = employee_id or f"EMP{idx:03d}{(username or 'USER')[:8].upper()}"
                    user_defaults = {
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "is_active": True,
                        # CustomUser fields
                        "employee_id": emp_id_default,
                        "role": role,
                        "department": department if department else None,
                        # Permissions
                        "is_staff": True if role in ["manager", "hr", "admin"] else False,
                        "is_superuser": True if role == "admin" else False,
                    }
                    # Remove None values to avoid passing invalid defaults
                    user_defaults = {k: v for k, v in user_defaults.items() if v is not None}
                    user, created = User.objects.get_or_create(username=username, defaults=user_defaults)

                    changed = False
                    # Update simple fields
                    for attr, val in user_defaults.items():
                        if getattr(user, attr) != val and val is not None:
                            setattr(user, attr, val)
                            changed = True

                    # Custom fields
                    if getattr(user, "role", None) != role:
                        try:
                            setattr(user, "role", role)
                        except Exception:
                            pass
                        changed = True
                    if department and hasattr(user, "department"):
                        try:
                            setattr(user, "department", department)
                        except Exception:
                            pass
                        changed = True
                    if hasattr(user, "employee_id") and not getattr(user, "employee_id", None):
                        # Generate a simple employee_id if not provided
                        try:
                            setattr(user, "employee_id", employee_id or f"EMP{idx:03d}")
                        except Exception:
                            pass
                        changed = True

                    # Staff flag for manager/admin
                    if role in ["manager", "hr", "admin"] and not user.is_staff:
                        user.is_staff = True
                        changed = True
                    if role == "admin" and not user.is_superuser:
                        user.is_superuser = True
                        changed = True

                    if changed:
                        user.save()

                    # Set/Update password if provided
                    if password:
                        user.set_password(password)
                        user.save(update_fields=["password"])

                    self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} user: {username} ({role}) in {dept_name}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error seeding users from SEED_USERS: {e}"))
        else:
            self.stdout.write("No SEED_USERS provided; skipping user seeding.")

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
                        else:
                            # If existing record has 0 entitlement, bump to defaults
                            if getattr(lb, "entitled_days", 0) == 0:
                                lb.entitled_days = entitlement
                                # Ensure used/pending do not exceed entitlement
                                if lb.used_days > lb.entitled_days:
                                    lb.used_days = lb.entitled_days
                                if lb.pending_days > (lb.entitled_days - lb.used_days):
                                    lb.pending_days = max(0, lb.entitled_days - lb.used_days)
                                lb.save(update_fields=["entitled_days", "used_days", "pending_days", "updated_at"])
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"Updated entitlement for {user.email or user.username} - {lt.name} to {entitlement}"
                                    )
                                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error seeding leave types/balances: {e}"))

        # Optional: add more seed logic here (departments, initial roles, etc.)
        self.stdout.write(self.style.SUCCESS("setup_production_data completed."))