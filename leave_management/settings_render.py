import os
import dj_database_url
from decouple import config
from .settings import *

# Override settings for Render deployment
DEBUG = False

# Security
ALLOWED_HOSTS = [
    '.onrender.com',
    'localhost',
    '127.0.0.1'
]

# Database configuration for Render PostgreSQL
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    # Fallback to SQLite for local testing
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Templates configuration for serving React app
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
                os.path.join(BASE_DIR, 'frontend', 'build'),  # React build directory (prefer this)
                os.path.join(BASE_DIR, 'templates'),
            ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# React build files location
REACT_BUILD_DIR = os.path.join(BASE_DIR, 'frontend', 'build')

# Use WhiteNoise for static files serving
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Additional directories for static files (includes React build)
STATICFILES_DIRS = [
    REACT_BUILD_DIR,
] if os.path.exists(REACT_BUILD_DIR) else []

# CORS configuration for frontend
# On Render, frontend and backend are served from same domain, so we need to allow same-origin
CORS_ORIGINS_STR = os.environ.get('CORS_ALLOWED_ORIGINS', 'https://leave-management-app-w7zp.onrender.com')
CORS_ALLOWED_ORIGINS = CORS_ORIGINS_STR.split(',') if ',' in CORS_ORIGINS_STR else [CORS_ORIGINS_STR]

# For unified deployment, allow same-origin requests
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Allow all origins only in debug mode

# Additional CORS settings for API endpoints
CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Media files (for file uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# --- AUTO DATABASE SETUP TRIGGER FOR RENDER ---
# Note: Management commands will run after Django is fully initialized via AppConfig

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}