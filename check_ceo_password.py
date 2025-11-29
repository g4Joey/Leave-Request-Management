#!/usr/bin/env python
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

ceo = User.objects.filter(email='ceo@umbcapital.com').first()
if ceo:
    print(f"CEO: {ceo.email}")
    print(f"Username: {ceo.username}")
    print(f"Is Active: {ceo.is_active}")
    print(f"Check password '1234': {ceo.check_password('1234')}")
    
    # Try all possible passwords
    for pwd in ['password', 'admin', 'ceo', '1234', 'ceo1234', 'umbcapital']:
        if ceo.check_password(pwd):
            print(f"\n✓ PASSWORD FOUND: {pwd}")
            break
else:
    print("CEO not found")
