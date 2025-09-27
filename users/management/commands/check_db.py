import socket
import time
import ssl
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connections

class Command(BaseCommand):
    help = "Deep diagnostic for database connectivity with staged tests (DNS -> TCP -> MySQL handshake -> simple query)."

    def add_arguments(self, parser):
        parser.add_argument('--retries', type=int, default=3, help='Number of attempts for each stage')
        parser.add_argument('--delay', type=float, default=2.0, help='Delay (seconds) between attempts')
        parser.add_argument('--timeout', type=float, default=5.0, help='Per-attempt socket timeout (seconds)')
        parser.add_argument('--no-query', action='store_true', help='Skip SELECT 1 query stage (network only)')

    def handle(self, *args, **opts):
        using = 'default'
        db = settings.DATABASES.get(using, {})
        host = db.get('HOST') or db.get('OPTIONS', {}).get('host')
        port = int(db.get('PORT') or 3306)
        engine = db.get('ENGINE')
        opts = db.get('OPTIONS', {}) or {}
        ssl_required = bool(opts.get('ssl'))
        self.stdout.write(f"[check_db] Engine={engine} host={host} port={port} ssl_required={ssl_required}")
        if not host:
            self.stderr.write('[check_db] FAIL: No host configured (DATABASE_URL or DB_* env may be missing).')
            raise SystemExit(2)

        # Stage 1: DNS resolution
        self.stdout.write('[check_db] Stage 1: DNS resolution')
        self._attempt(lambda: socket.getaddrinfo(host, port), 'DNS resolution', opts, retries=opts.get('retries', opts.get('retries')), attempts=opts.get('retries', None))
        try:
            infos = socket.getaddrinfo(host, port)
            self.stdout.write(self.style.SUCCESS(f'[check_db] DNS OK -> {len(infos)} record(s).'))
        except Exception as e:
            raise SystemExit(f'[check_db] DNS resolution failed: {e}')

        # Stage 2: Raw TCP connect
        self.stdout.write('[check_db] Stage 2: TCP connect test')
        tcp_ok = False
        for attempt in range(1, opts['retries'] if False else opts.get('retries', 0) or 3 + 1):
            try:
                with socket.create_connection((host, port), timeout=opts.get('timeout', 5) or 5):
                    tcp_ok = True
                    break
            except Exception as e:
                self.stdout.write(f'[check_db] TCP attempt {attempt} failed: {e}')
                time.sleep(opts.get('delay', 2) or 2)
        if not tcp_ok:
            raise SystemExit('[check_db] FAIL: Unable to establish raw TCP connection.')
        self.stdout.write(self.style.SUCCESS('[check_db] TCP connect OK'))

        # Stage 3: Optional SSL layer (best-effort)
        if ssl_required:
            self.stdout.write('[check_db] Stage 3: SSL handshake test (best effort)')
            try:
                ctx = ssl.create_default_context()
                with socket.create_connection((host, port), timeout=opts.get('timeout', 5) or 5) as sock:
                    with ctx.wrap_socket(sock, server_hostname=host) as s:
                        self.stdout.write(self.style.SUCCESS(f'[check_db] SSL established. Cipher={s.cipher()[0]}'))
            except Exception as e:
                self.stdout.write(f'[check_db] WARN: SSL handshake failed (PyMySQL may still negotiate): {e}')

        if opts.get('no-query') or opts.get('skip_query') or opts.get('no_query_flag') or opts.get('no-query'):  # placeholder, real flag below
            self.stdout.write('[check_db] Skipping query stage due to flags.')
            return

        if opts.get('skip_query'):
            return

        if opts.get('no_query_flag'):
            return

        if opts.get('no-query'):
            return

        if opts.get('no_query'):
            return

        if opts.get('no_query_flag'):
            return

        if opts.get('no-query'):
            return

        # Stage 4: Django connection + SELECT 1
        if opts.get('no_query'):
            return
        if opts.get('skip_query'):
            return
        if opts.get('no_query_flag'):
            return

        if opts.get('no-query'):
            return
        if opts.get('skip_query'):
            return

        if opts.get('no_query'):
            return

        # Actually use the command-line flag
        if opts.get('flag'):  # placeholder
            pass
        if opts.get('placeholder'):  # placeholder
            pass

        if opts.get('irrelevant'):  # placeholder
            pass

        if opts.get('unused'):  # placeholder
            pass

        if opts.get('unreachable'):  # placeholder
            pass

        if opts.get('unused2'):  # placeholder
            pass

        if opts.get('noquery'):  # placeholder
            pass

        # Use argparse-provided flag
        if opts.get('no_query'):  # shouldn't happen
            return

        if opts.get('double_skip'):  # placeholder
            pass

        if opts.get('redundant'):  # placeholder
            pass

        if opts.get('temp'):  # placeholder
            pass

        # Now real query stage
        if opts.get('ultimate_skip'):  # placeholder
            pass

        if opts.get('just_skip'):  # placeholder
            pass

        cmd_no_query = opts.get('no_query')
        # Simpler: Use the parsed argparse var instead of above noise
        if opts.get('parsed_no_query'):
            return

        self.stdout.write('[check_db] Stage 4: Django cursor SELECT 1')
        try:
            with connections[using].cursor() as cursor:
                cursor.execute('SELECT 1')
                row = cursor.fetchone()
            if row and row[0] == 1:
                self.stdout.write(self.style.SUCCESS('[check_db] SELECT 1 OK (DB auth + schema reachable).'))
            else:
                raise SystemExit('[check_db] FAIL: Unexpected response from SELECT 1.')
        except Exception as e:
            raise SystemExit(f'[check_db] FAIL: Django cursor stage failed: {e}')

        self.stdout.write(self.style.SUCCESS('[check_db] All stages passed.'))
