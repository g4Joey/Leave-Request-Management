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

        if su_username and su_password:
            user, created = User.objects.get_or_create(
                username=su_username,
                defaults={
                    "email": su_email or "",
                    "is_staff": True,
                    "is_superuser": True,
                },
            )
            if created:
                user.set_password(su_password)
                user.save(update_fields=["password"])
                self.stdout.write(self.style.SUCCESS(f"Created superuser '{su_username}'"))
            else:
                # Ensure the flags are correct even if user already existed
                update_fields = []
                if not user.is_staff:
                    user.is_staff = True
                    update_fields.append("is_staff")
                if not user.is_superuser:
                    user.is_superuser = True
                    update_fields.append("is_superuser")
                if update_fields:
                    user.save(update_fields=update_fields)
                self.stdout.write(self.style.WARNING(f"Superuser '{su_username}' already exists; ensured permissions."))
        else:
            self.stdout.write("No DJANGO_SUPERUSER_* env vars set; skipping superuser creation.")

        # Optional: add more seed logic here (departments, initial roles, etc.)
        self.stdout.write(self.style.SUCCESS("setup_production_data completed."))