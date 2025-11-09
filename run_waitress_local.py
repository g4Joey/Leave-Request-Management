import os
import sys

# Configure environment for production-like run (use base settings with SQLite locally)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
os.environ.setdefault('DJANGO_DEBUG', '0')
os.environ.setdefault('ALLOWED_HOSTS', 'localhost,127.0.0.1')
os.environ.setdefault('USE_SQLITE', '1')  # quick local DB

# Ensure Django is setup before waitress imports wsgi app
import django
from django.core.wsgi import get_wsgi_application

django.setup()

# Collect static automatically on first run if missing (best-effort)
try:
    from django.conf import settings
    static_root = getattr(settings, 'STATIC_ROOT', None)
    if static_root and not os.path.exists(static_root):
        from django.core.management import call_command
        call_command('migrate', interactive=False)
        call_command('collectstatic', interactive=False, verbosity=0, clear=False, ignore_patterns=['*.map'])
except Exception as e:
    print('Warning: migrate/collectstatic step failed or skipped:', e)

# Start waitress
from waitress import serve
application = get_wsgi_application()

port = int(os.environ.get('PORT', '8000'))
print(f"Starting waitress on http://127.0.0.1:{port} (production-like) ...")
serve(application, host='127.0.0.1', port=port)
