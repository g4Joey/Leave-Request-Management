#!/usr/bin/env python
"""
CEO Account Diagnostic Script
Check if CEO user exists and troubleshoot login issues
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

def diagnose_ceo_account():
    """Diagnose CEO account issues"""
    print("=== CEO Account Diagnostics ===")
    
    # Check for any CEO users
    ceo_users = User.objects.filter(role='ceo')
    print(f"CEO users found: {ceo_users.count()}")
    
    for user in ceo_users:
        print(f"\n👤 CEO User: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Full Name: {user.get_full_name()}")
        print(f"   Active: {user.is_active}")
        print(f"   Active Employee: {getattr(user, 'is_active_employee', 'N/A')}")
        print(f"   Staff: {user.is_staff}")
        print(f"   Department: {getattr(user.department, 'name', 'None') if hasattr(user, 'department') else 'N/A'}")
    
    # Check environment variables (safely)
    print(f"\n🔧 Environment Variables:")
    print(f"   CEO_EMAIL set: {'Yes' if os.getenv('CEO_EMAIL') else 'No'}")
    print(f"   CEO_PASSWORD set: {'Yes' if os.getenv('CEO_PASSWORD') else 'No'}")
    print(f"   CEO_FIRST_NAME set: {'Yes' if os.getenv('CEO_FIRST_NAME') else 'No'}")
    print(f"   CEO_LAST_NAME set: {'Yes' if os.getenv('CEO_LAST_NAME') else 'No'}")
    
    # Check for any users with the target email
    target_email = os.getenv('CEO_EMAIL', 'ceo@umbcapital.com')
    email_users = User.objects.filter(email=target_email)
    print(f"\n📧 Users with email '{target_email}': {email_users.count()}")
    for user in email_users:
        print(f"   - {user.username} (role: {getattr(user, 'role', 'unknown')}, active: {user.is_active})")
    
    # Test authentication if we have credentials
    ceo_email = os.getenv('CEO_EMAIL')
    ceo_password = os.getenv('CEO_PASSWORD')
    
    if ceo_email and ceo_password:
        print(f"\n🔑 Testing authentication...")
        # Try to authenticate with email
        auth_user = authenticate(username=ceo_email, password=ceo_password)
        if auth_user:
            print(f"   ✅ Authentication successful with email")
        else:
            print(f"   ❌ Authentication failed with email")
            
            # Try to find user by email and test with username
            try:
                user_by_email = User.objects.get(email=ceo_email)
                auth_user = authenticate(username=user_by_email.username, password=ceo_password)
                if auth_user:
                    print(f"   ✅ Authentication successful with username: {user_by_email.username}")
                else:
                    print(f"   ❌ Authentication failed with username: {user_by_email.username}")
            except User.DoesNotExist:
                print(f"   ❌ No user found with email: {ceo_email}")

def fix_ceo_account():
    """Create or fix CEO account"""
    print("\n=== CEO Account Fix ===")
    
    ceo_email = os.getenv('CEO_EMAIL', 'ceo@umbcapital.com')
    ceo_password = os.getenv('CEO_PASSWORD', 'MerbanCEO')
    ceo_first_name = os.getenv('CEO_FIRST_NAME', 'Benjamin')
    ceo_last_name = os.getenv('CEO_LAST_NAME', 'Ackah')
    
    # Check if user exists by email
    try:
        existing_user = User.objects.get(email=ceo_email)
        print(f"Found existing user with email: {existing_user.username}")
        
        # Update the user
        existing_user.first_name = ceo_first_name
        existing_user.last_name = ceo_last_name
        existing_user.role = 'ceo'
        existing_user.is_active = True
        existing_user.is_staff = True
        if hasattr(existing_user, 'is_active_employee'):
            existing_user.is_active_employee = True
        
        # Reset password
        existing_user.set_password(ceo_password)
        
        # Ensure department
        executive_dept, created = Department.objects.get_or_create(
            name='Executive',
            defaults={'description': 'Executive leadership team'}
        )
        if hasattr(existing_user, 'department'):
            existing_user.department = executive_dept
        
        existing_user.save()
        print(f"✅ Updated existing CEO user: {existing_user.username}")
        
    except User.DoesNotExist:
        print(f"No existing user found. Creating new CEO user...")
        
        # Create Executive department
        executive_dept, created = Department.objects.get_or_create(
            name='Executive',
            defaults={'description': 'Executive leadership team'}
        )
        
        # Create CEO user
        username = ceo_email.split('@')[0]  # Extract username from email
        
        new_user = User.objects.create_user(
            username=username,
            email=ceo_email,
            password=ceo_password,
            first_name=ceo_first_name,
            last_name=ceo_last_name,
            employee_id='CEO001',
            role='ceo',
            department=executive_dept,
            is_staff=True,
            annual_leave_entitlement=30,
            is_active_employee=True
        )
        print(f"✅ Created new CEO user: {new_user.username}")
    
    # Test authentication
    print(f"\n🔑 Testing login after fix...")
    auth_user = authenticate(username=ceo_email, password=ceo_password)
    if auth_user:
        print(f"✅ CEO can now log in with: {ceo_email}")
    else:
        # Try with username
        try:
            user = User.objects.get(email=ceo_email)
            auth_user = authenticate(username=user.username, password=ceo_password)
            if auth_user:
                print(f"✅ CEO can log in with username: {user.username}")
            else:
                print(f"❌ Authentication still failing")
        except User.DoesNotExist:
            print(f"❌ User not found after creation")

if __name__ == '__main__':
    diagnose_ceo_account()
    
    # Ask if user wants to fix the account
    response = input("\nDo you want to create/fix the CEO account? (y/N): ")
    if response.lower() == 'y':
        fix_ceo_account()