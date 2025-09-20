#!/usr/bin/env python
"""
Test database connection for DigitalOcean deployment
"""
import os
import django
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings_production')
django.setup()

def test_db_connection():
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        print("✅ Database connection successful!")
        print(f"Result: {result}")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_settings():
    print("=== Django Settings Test ===")
    print(f"DEBUG: {settings.DEBUG}")
    print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    print(f"DATABASE ENGINE: {settings.DATABASES['default']['ENGINE']}")
    print(f"DATABASE NAME: {settings.DATABASES['default'].get('NAME', 'Not set')}")
    print(f"DATABASE HOST: {settings.DATABASES['default'].get('HOST', 'Not set')}")

if __name__ == "__main__":
    print("=== Testing DigitalOcean Production Settings ===")
    
    # Set environment variables for testing
    os.environ['DATABASE_URL'] = "mysql://doadmin:PLACEHOLDER_PASSWORD@db-mysql-nyc3-43467-do-user-24806705-0.k.db.ondigitalocean.com:25060/defaultdb?ssl-mode=REQUIRED"
    os.environ['DEBUG'] = "False"
    os.environ['ALLOWED_HOSTS'] = "takeabreak-app-38abv.ondigitalocean.app,localhost,127.0.0.1"
    
    test_settings()
    print("\n=== Testing Database Connection ===")
    test_db_connection()