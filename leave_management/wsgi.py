"""
WSGI config for leave_management project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Use environment-specified settings module, with production as fallback
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings_production')

application = get_wsgi_application()
