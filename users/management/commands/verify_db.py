from django.core.management.base import BaseCommand
from django.db import connections
from django.conf import settings

class Command(BaseCommand):
    help = "Verify production database connectivity and engine correctness. Exits with non-zero status on failure."

    def handle(self, *args, **options):
        using = 'default'
        db_settings = settings.DATABASES.get(using, {})
        engine = db_settings.get('ENGINE')
        self.stdout.write(f"[verify_db] Engine: {engine}")
        if 'mysql' not in (engine or ''):
            raise SystemExit("[verify_db] ERROR: Non-MySQL engine detected. Aborting.")
        try:
            with connections[using].cursor() as cursor:
                cursor.execute("SELECT 1")
                row = cursor.fetchone()
            if row and row[0] == 1:
                self.stdout.write(self.style.SUCCESS('[verify_db] Database connectivity OK.'))
            else:
                raise SystemExit('[verify_db] Unexpected response from SELECT 1.')
        except Exception as e:
            raise SystemExit(f"[verify_db] ERROR: {e}")
