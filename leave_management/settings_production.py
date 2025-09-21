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

# Database Configuration for DigitalOcean
if 'DATABASE_URL' in os.environ:
    # Parse the DATABASE_URL for MySQL, but be robust to blanks/invalid values during build
    raw = os.environ.get('DATABASE_URL', '')
    db_url = (raw or '').strip()
    if db_url and '://' in db_url:
        try:
            db_config = dj_database_url.parse(db_url, conn_max_age=600, conn_health_checks=True)

            # Ensure MySQL engine and options for DigitalOcean MySQL
            db_config['ENGINE'] = 'django.db.backends.mysql'
            db_config['OPTIONS'] = {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'charset': 'utf8mb4',
                'ssl': {'ssl-mode': 'PREFERRED'},  # Changed from REQUIRED to PREFERRED for better compatibility
                'connect_timeout': 60,
                'read_timeout': 60,
                'write_timeout': 60,
            }

            DATABASES = {
                'default': db_config
            }
        except Exception:
            # Fall through to alternative configs without breaking build
            pass
elif all(key in os.environ for key in ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']):
    # Alternative: Use individual environment variables
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
            },
        }
    }
else:
    # Fallback to local settings from base settings.py
    pass

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
