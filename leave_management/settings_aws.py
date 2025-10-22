"""
AWS production-compatible settings for quick free-tier deployment.

This file intentionally supports a lightweight SQLite fallback when
deploying to Elastic Beanstalk on the free tier for testing. It also
reads standard environment variables for secrets and database settings
when you later attach an RDS instance.

Usage:
  - For quick testing on free-tier EB: set USE_SQLITE=1 in EB environment.
  - For production with RDS: set DATABASE_URL or DB_* variables.
"""
from .settings import *
import os
import dj_database_url

# Keep debug off by default unless explicitly enabled
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Secret key from env
SECRET_KEY = os.getenv('SECRET_KEY', SECRET_KEY)

# Allowed hosts - default to wildcard for EB environment but prefer explicit
raw_hosts = os.getenv('ALLOWED_HOSTS', os.getenv('ALLOWED_HOSTS', '*'))
ALLOWED_HOSTS = [h.strip() for h in raw_hosts.split(',') if h.strip()]

# Static files
STATIC_URL = '/django-static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Database configuration: REQUIRE a proper database in production (no SQLite fallback)
# This avoids accidental ephemeral data loss. Set DATABASE_URL or DB_HOST/DB_NAME/DB_USER/DB_PASSWORD.
_db_configured = False
if 'DATABASE_URL' in os.environ:
    try:
        db_config = dj_database_url.parse(os.environ.get('DATABASE_URL'), conn_max_age=600)
        DATABASES = {'default': db_config}
        _db_configured = True
    except Exception:
        _db_configured = False

if not _db_configured and all(k in os.environ for k in ('DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD')):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME'),
            'USER': os.environ.get('DB_USER'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
            'HOST': os.environ.get('DB_HOST'),
            'PORT': os.environ.get('DB_PORT', '3306'),
        }
    }
    _db_configured = True

if not _db_configured:
    raise RuntimeError(
        "Database not configured for AWS deployment. Set DATABASE_URL or DB_HOST/DB_NAME/DB_USER/DB_PASSWORD."
    )

# WhiteNoise
MIDDLEWARE = list(MIDDLEWARE)
if 'whitenoise.middleware.WhiteNoiseMiddleware' not in MIDDLEWARE:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Security (minimal for quick EB testing; tighten for real prod)
if not DEBUG:
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() in {'1', 'true', 'yes'}
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Elastic Beanstalk specific: allow proxy headers
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Email fallback to console in testing
if not os.getenv('EMAIL_HOST'):
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
