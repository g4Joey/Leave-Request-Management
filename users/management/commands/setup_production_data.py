from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os


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
            # Ensure required fields for CustomUser are provided
            defaults = {
                "email": su_email or "",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "first_name": su_first_name,
                "last_name": su_last_name,
                "role": "admin",
                "employee_id": su_employee_id,
            }

            user, created = User.objects.get_or_create(
                username=su_username,
                defaults=defaults,
            )
            if created:
                user.set_password(su_password)
                user.save(update_fields=["password"])
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
                if not getattr(user, "employee_id", None):
                    user.employee_id = su_employee_id
                    update_fields.append("employee_id")
                if hasattr(user, "role") and user.role != "admin":
                    user.role = "admin"
                    update_fields.append("role")
                if update_fields:
                    user.save(update_fields=update_fields)
                self.stdout.write(self.style.WARNING(f"Superuser '{su_username}' already exists; ensured permissions."))
        else:
            self.stdout.write("No DJANGO_SUPERUSER_* env vars set; skipping superuser creation.")

        # Optional: add more seed logic here (departments, initial roles, etc.)
        self.stdout.write(self.style.SUCCESS("setup_production_data completed."))