import os
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connection


class Command(BaseCommand):
    help = (
        "Load a full JSON dump (created via dumpdata) into the current database. "
        "Intended for a freshly provisioned production database. Fails if core tables already contain data unless --force is passed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_path', nargs='?', default='data-backup-2025-09-26.json',
            help='Path to the JSON dump file (default: data-backup-2025-09-26.json)'
        )
        parser.add_argument('--force', action='store_true', help='Bypass safety checks about existing data.')
        parser.add_argument('--dry-run', action='store_true', help='Parse file and report stats without loading.')

    def handle(self, *args, **options):
        backup_path = options['backup_path']
        force = options['force']
        dry_run = options['dry_run']

        path = Path(backup_path)
        if not path.exists():
            raise CommandError(f'Backup file not found: {backup_path}')

        # Minimal heuristic: ensure key domain tables are empty to reduce PK collision risk.
        existing_counts = self._collect_counts()
        populated = {k: v for k, v in existing_counts.items() if v > 0}
        if populated and not force:
            msg_lines = ["Refusing to load backup: database already has data in these tables:"]
            for k, v in populated.items():
                msg_lines.append(f"  - {k}: {v} rows")
            msg_lines.append("Re-run with --force to override (will likely raise IntegrityError on duplicates).")
            raise CommandError("\n".join(msg_lines))

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry-run mode: reading JSON to show basic stats...'))
            stats = self._inspect_file(path)
            for model, count in stats.items():
                self.stdout.write(f"  {model}: {count}")
            self.stdout.write(self.style.SUCCESS('Dry-run complete; no data loaded.'))
            return

        self.stdout.write(f'Loading backup from {backup_path} ...')
        try:
            # Use Django's loaddata; rely on the fixture format correctness.
            call_command('loaddata', str(path), verbosity=1)
            self.stdout.write(self.style.SUCCESS('Backup load completed.'))
        except Exception as e:
            raise CommandError(f'Backup load failed: {e}')

    def _collect_counts(self):
        """Return counts for sentinel tables to detect existing data."""
        counts = {}
        with connection.cursor() as cur:
            for table in [
                'users_customuser',
                'leaves_leaverequest',
                'users_department',
                'notifications_notification',
            ]:
                try:
                    cur.execute(f'SELECT COUNT(*) FROM {table}')
                    counts[table] = cur.fetchone()[0]
                except Exception:
                    counts[table] = -1  # table may not exist yet
        return counts

    def _inspect_file(self, path: Path):
        """Read the JSON (streaming) and count objects per model label."""
        try:
            with path.open('r', encoding='utf-8') as fh:
                data = json.load(fh)
        except Exception as e:
            raise CommandError(f'Failed to parse JSON: {e}')
        stats = {}
        if isinstance(data, list):
            for obj in data:
                mdl = obj.get('model', 'UNKNOWN')
                stats[mdl] = stats.get(mdl, 0) + 1
        return stats
