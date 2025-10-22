"""
Production Password Change Script
Change password for any user in production
"""

import os
import django
import sys
from getpass import getpass

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings_production')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()


def change_user_password():
    """Change password for a user"""
    
    print("🔒 Password Change Tool")
    print("=" * 30)
    
    # Get user identifier
    user_email = input("Enter user email: ").strip()
    if not user_email:
        print("❌ Email is required!")
        return False
    
    # Find user
    try:
        user = User.objects.get(email=user_email)
        print(f"✅ Found user: {user.first_name} {user.last_name} ({user.username})")
    except User.DoesNotExist:
        print(f"❌ No user found with email: {user_email}")
        return False
    
    # Get new password
    print("\n🔑 Enter new password:")
    new_password = getpass("New Password: ")
    confirm_password = getpass("Confirm Password: ")
    
    if new_password != confirm_password:
        print("❌ Passwords don't match!")
        return False
    
    if len(new_password) < 8:
        print("❌ Password must be at least 8 characters!")
        return False
    
    # Change password
    try:
        user.set_password(new_password)
        user.save()
        
        print("\n🎉 SUCCESS! Password changed!")
        print(f"   👤 User: {user.email}")
        print(f"   🔑 New password set successfully!")
        print("\n💡 You can now login with the new password!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error changing password: {e}")
        return False


if __name__ == "__main__":
    change_user_password()