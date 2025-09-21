"""
ASGI config for leave_management project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

# Prefer production settings by default in deployed environments.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings_production')

application = get_asgi_application()
