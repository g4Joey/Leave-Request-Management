"""
Production settings for Leave Management System on DigitalOcean
"""
from .settings import *
import os
import dj_database_url

# MySQL configuration for production
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'your-default-secret-key-change-this')

# ALLOWED HOSTS
# - Accept from env, but be robust (strip spaces) and ensure DigitalOcean app host pattern is included
raw_hosts = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,.ondigitalocean.app')
ALLOWED_HOSTS = [h.strip() for h in raw_hosts.split(',') if h.strip()]
if '.ondigitalocean.app' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('.ondigitalocean.app')  # allow any DO app subdomain

# CSRF trusted origins derived from allowed hosts (scheme required)
CSRF_TRUSTED_ORIGINS = []
for h in ALLOWED_HOSTS:
    if h in ('*', 'localhost', '127.0.0.1') or h.startswith('localhost') or h.startswith('127.0.0.1'):
        continue
    # For leading dot, add wildcard-compatible origin by stripping leading dot
    host = h.lstrip('.')
    CSRF_TRUSTED_ORIGINS.append(f"https://{host}")

"""Database Configuration for DigitalOcean

Order attempted:
1) DATABASE_URL (if present and valid)
2) Individual DB_* env vars (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)

Previously this file contained a silent fallback to SQLite when neither was
configured, which masked production misconfiguration and caused data loss
between deploys. Per hardening request, that fallback has been REMOVED.
If no production database settings are found we now raise a RuntimeError
to fail fast during build / startup.
"""

_db_configured = False

if 'DATABASE_URL' in os.environ:
    # Parse the DATABASE_URL for MySQL, but be robust to blanks/invalid values during build
    raw = os.environ.get('DATABASE_URL', '')
    db_url = (raw or '').strip()
    if db_url and '://' in db_url:
        try:
            db_config = dj_database_url.parse(db_url, conn_max_age=600, conn_health_checks=True)

            # Ensure MySQL engine and options for DigitalOcean MySQL
            db_config['ENGINE'] = 'django.db.backends.mysql'
            # Allow operator to tune base timeout; FAST_DB_FAIL halves it.
            fast_fail = os.getenv('FAST_DB_FAIL', '0').lower() in {'1', 'true', 'yes'}
            configured_timeout = os.getenv('DB_TIMEOUT')  # seconds
            try:
                configured_timeout_val = int(configured_timeout) if configured_timeout else None
            except ValueError:
                configured_timeout_val = None
            base_timeout = configured_timeout_val or 12
            if fast_fail:
                base_timeout = max(3, base_timeout // 2)
            db_config['OPTIONS'] = {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'charset': 'utf8mb4',
                # Enforce SSL; DigitalOcean managed MySQL supports REQUIRED.
                'ssl': {'ssl-mode': 'REQUIRED'},
                'connect_timeout': base_timeout,
                'read_timeout': base_timeout,
                'write_timeout': base_timeout,
            }

            DATABASES = {
                'default': db_config
            }
            _db_configured = True
        except Exception:
            # Fall through to alternative configs without breaking build
            pass

if not _db_configured and all(key in os.environ for key in ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']):
    # Alternative: Use individual environment variables
    fast_fail = os.getenv('FAST_DB_FAIL', '0').lower() in {'1', 'true', 'yes'}
    configured_timeout = os.getenv('DB_TIMEOUT')
    try:
        configured_timeout_val = int(configured_timeout) if configured_timeout else None
    except ValueError:
        configured_timeout_val = None
    base_timeout = configured_timeout_val or 12
    if fast_fail:
        base_timeout = max(3, base_timeout // 2)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME'),
            'USER': os.environ.get('DB_USER'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
            'HOST': os.environ.get('DB_HOST'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'charset': 'utf8mb4',
                'ssl': {'ssl-mode': 'REQUIRED'},
                'connect_timeout': base_timeout,
                'read_timeout': base_timeout,
                'write_timeout': base_timeout,
            },
        }
    }
    _db_configured = True

if not _db_configured:
    raise RuntimeError(
        "Production database not configured. Set DATABASE_URL or DB_HOST/DB_NAME/DB_USER/DB_PASSWORD env vars. "
        "(SQLite fallback removed intentionally to prevent accidental ephemeral data usage.)"
    )

# Optional one-time logging of DB config (without credentials) to aid diagnosis
if os.getenv('LOG_DB_CONFIG', '0').lower() in {'1', 'true', 'yes'} and _db_configured:
    import logging
    _db = DATABASES.get('default', {})
    _opts = _db.get('OPTIONS') or {}
    safe_snapshot = {
        'ENGINE': _db.get('ENGINE'),
        'HOST': _db.get('HOST') or _opts.get('host'),
        'PORT': _db.get('PORT'),
        'NAME': _db.get('NAME'),
        'OPTIONS': {
            'ssl': _opts.get('ssl'),
            'connect_timeout': _opts.get('connect_timeout'),
            'read_timeout': _opts.get('read_timeout'),
            'write_timeout': _opts.get('write_timeout'),
        }
    }
    logging.getLogger('users').info('DB CONFIG SNAPSHOT (sanitized): %s', safe_snapshot)

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# In production, serve Django static under a distinct prefix to avoid
# clashing with the React app's '/static' assets served by the frontend service.
STATIC_URL = '/django-static/'

# WhiteNoise configuration
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# CORS settings for frontend
cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', 'https://takeabreak-app-38abv.ondigitalocean.app')
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(',') if origin.strip()]
CORS_ALLOW_CREDENTIALS = True

# Additional CORS settings
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Only allow all origins in development

# Security settings for production
if not DEBUG:
    # Security headers
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    
    # Session security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True

from django.core.management import call_command
import sys

# --- AUTO DATABASE SETUP TRIGGER ---
if os.getenv('SETUP_FRESH_DATABASE', '0').lower() in {'1', 'true', 'yes'}:
    try:
        print('==> Running setup_fresh_database management command (auto-triggered by SETUP_FRESH_DATABASE)...')
        call_command('setup_fresh_database')
        print('==> setup_fresh_database completed.')
    except Exception as e:
        print(f'!! Error running setup_fresh_database: {e}')
        # Print full traceback for debugging
        import traceback
        traceback.print_exc()

# --- AUTO DATA FIX TRIGGER (for existing databases) ---
if os.getenv('RUN_FIX_PRODUCTION_DATA', '0').lower() in {'1', 'true', 'yes'}:
    try:
        print('==> Running fix_production_data management command (auto-triggered by RUN_FIX_PRODUCTION_DATA)...')
        call_command('fix_production_data')
        print('==> fix_production_data completed.')
    except Exception as e:
        print(f'!! Error running fix_production_data: {e}')
        # Print full traceback for debugging
        import traceback
        traceback.print_exc()

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG' if DEBUG else 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'leave_management': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'leaves': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'users': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# Show SQL queries in debug mode
if DEBUG:
    LOGGING['loggers']['django.db.backends']['level'] = 'DEBUG'

# Cache configuration (optional)
if 'REDIS_URL' in os.environ:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.environ.get('REDIS_URL'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }

# Email configuration (for notifications)
if 'EMAIL_HOST' in os.environ:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@example.com')
