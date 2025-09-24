from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connections
import os


class Command(BaseCommand):
    help = "Show the active database engine and connection details (sanitized), and verify connectivity."

    def add_arguments(self, parser):
        parser.add_argument(
            "--check", action="store_true", help="Attempt to connect and fetch server version"
        )

    def handle(self, *args, **options):
        db = settings.DATABASES.get("default", {})
        engine = db.get("ENGINE", "")
        name = db.get("NAME", "")
        host = db.get("HOST", "")
        port = db.get("PORT", "")
        user = db.get("USER", "")

        # Environment hints (without exposing secrets)
        env_hints = {
            "DJANGO_SETTINGS_MODULE": os.getenv("DJANGO_SETTINGS_MODULE"),
            "DATABASE_URL": bool(os.getenv("DATABASE_URL")),
            "DB_ENGINE": os.getenv("DB_ENGINE"),
            "USE_SQLITE": os.getenv("USE_SQLITE"),
            "DB_HOST": bool(os.getenv("DB_HOST")),
            "DB_NAME": bool(os.getenv("DB_NAME")),
            "DB_USER": bool(os.getenv("DB_USER")),
            "DB_PASSWORD": bool(os.getenv("DB_PASSWORD")),
        }

        self.stdout.write(self.style.MIGRATE_HEADING("Active database configuration (sanitized):"))
        self.stdout.write(f"ENGINE: {engine}")
        self.stdout.write(f"NAME: {name}")
        self.stdout.write(f"HOST: {host}")
        self.stdout.write(f"PORT: {port}")
        self.stdout.write(f"USER: {user}")

        if "sqlite" in (engine or ""):
            self.stdout.write(self.style.WARNING("Note: Using SQLite (likely a fallback if in production)."))

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Environment hints (True means variable is present):"))
        for k, v in env_hints.items():
            self.stdout.write(f"{k}: {v}")

        if options.get("check"):
            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING("Connectivity check:"))
            conn = connections["default"]
            try:
                with conn.cursor() as cursor:
                    version = None
                    current_db = None
                    if "mysql" in engine:
                        cursor.execute("SELECT VERSION()")
                        version = cursor.fetchone()[0]
                        cursor.execute("SELECT DATABASE()")
                        current_db = cursor.fetchone()[0]
                    elif "postgresql" in engine or "postgres" in engine:
                        cursor.execute("SHOW server_version")
                        version = cursor.fetchone()[0]
                        cursor.execute("SELECT current_database()")
                        current_db = cursor.fetchone()[0]
                    elif "sqlite" in engine:
                        import sqlite3
                        version = sqlite3.sqlite_version
                        current_db = name
                    else:
                        cursor.execute("SELECT 1")
                        version = "unknown"

                self.stdout.write(self.style.SUCCESS("Connection OK"))
                if version:
                    self.stdout.write(f"Server version: {version}")
                if current_db:
                    self.stdout.write(f"Current database: {current_db}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Connection FAILED: {e}"))
