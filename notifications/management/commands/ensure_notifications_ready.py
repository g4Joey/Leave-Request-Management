from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection


DEFAULT_SETTINGS = {
    'OVERLAP_NOTIFY_MIN_DAYS': '3',
    'OVERLAP_NOTIFY_MIN_COUNT': '3',
    'OVERLAP_DETECT_ENABLED': 'true',
}


class Command(BaseCommand):
    help = "Ensure notifications app is ready: apply migrations and seed default SiteSetting keys if missing."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Checking notifications migrations and site settings..."))

        # 1) Apply notifications migrations explicitly (safe if already applied)
        try:
            call_command('migrate', 'notifications', verbosity=1)
            self.stdout.write(self.style.SUCCESS("✔ Notifications migrations are applied."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✖ Failed to apply notifications migrations: {e}"))
            self.stdout.write(self.style.WARNING("If the error mentions a missing table, run: python manage.py migrate notifications"))
            return

        # 2) Seed default SiteSetting keys
        try:
            from notifications.models import SiteSetting
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✖ Unable to import SiteSetting model: {e}"))
            return

        try:
            with connection.cursor() as cursor:
                # Check table existence in a backend-agnostic way
                table_names = connection.introspection.table_names()
                if 'notifications_sitesetting' not in table_names:
                    self.stdout.write(self.style.ERROR("✖ Table 'notifications_sitesetting' does not exist. Run: python manage.py migrate notifications"))
                    return
        except Exception:
            # If introspection fails, proceed and let ORM raise if truly missing
            pass

        created = 0
        for key, value in DEFAULT_SETTINGS.items():
            obj, was_created = SiteSetting.objects.update_or_create(
                key=key, defaults={'value': value}
            )
            created += 1 if was_created else 0

        if created:
            self.stdout.write(self.style.SUCCESS(f"✔ Seeded {created} default site setting(s)."))
        else:
            self.stdout.write(self.style.SUCCESS("✔ All default site settings already present."))

        self.stdout.write(self.style.SUCCESS("✅ Notifications app is ready."))
