#!/usr/bin/env python
"""
CEO Account Fix Script - Update existing CEO or create new one
"""

import os
import sys
import django

# Ensure project root is on sys.path when running as a script
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model, authenticate
from users.models import Department

User = get_user_model()

def fix_ceo_login():
    """Fix CEO login by updating existing CEO user with new credentials"""
    print("=== Fixing CEO Login ===")
    
    target_email = os.getenv('CEO_EMAIL', 'ceo@umbcapital.com')
    target_password = os.getenv('CEO_PASSWORD', 'MerbanCEO') 
    target_first_name = os.getenv('CEO_FIRST_NAME', 'Benjamin')
    target_last_name = os.getenv('CEO_LAST_NAME', 'Ackah')
    
    print(f"Target credentials: {target_email}")
    
    # Find existing CEO user
    existing_ceo = User.objects.filter(role='ceo').first()
    
    if existing_ceo:
        print(f"Found existing CEO: {existing_ceo.username} ({existing_ceo.email})")
        
        # Update the existing CEO with new credentials
        existing_ceo.email = target_email
        existing_ceo.username = target_email.split('@')[0]  # ceo@umbcapital.com -> ceo
        existing_ceo.first_name = target_first_name
        existing_ceo.last_name = target_last_name
        existing_ceo.is_active = True
        existing_ceo.is_staff = True
        if hasattr(existing_ceo, 'is_active_employee'):
            existing_ceo.is_active_employee = True
        
        # Set the new password
        existing_ceo.set_password(target_password)
        existing_ceo.save()
        
        print(f"✅ Updated CEO user successfully!")
        print(f"   Username: {existing_ceo.username}")
        print(f"   Email: {existing_ceo.email}")
        print(f"   Full Name: {existing_ceo.get_full_name()}")
        
        # Test authentication
        print(f"\n🔑 Testing authentication...")
        
        # Test with email
        auth_user = authenticate(username=target_email, password=target_password)
        if auth_user:
            print(f"✅ Can log in with EMAIL: {target_email}")
        else:
            print(f"❌ Cannot log in with email")
        
        # Test with username  
        auth_user = authenticate(username=existing_ceo.username, password=target_password)
        if auth_user:
            print(f"✅ Can log in with USERNAME: {existing_ceo.username}")
        else:
            print(f"❌ Cannot log in with username")
            
        print(f"\n✅ CEO login should now work!")
        print(f"📧 Use either: {target_email}")
        print(f"👤 Or username: {existing_ceo.username}")
        print(f"🔑 Password: [Your secure password]")
        
    else:
        print("❌ No existing CEO user found!")
        return False
    
    return True

if __name__ == '__main__':
    fix_ceo_login()