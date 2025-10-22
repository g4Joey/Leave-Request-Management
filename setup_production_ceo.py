"""
Production CEO Setup Script
This creates a CEO user specifically for production deployment
"""

import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings_production')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Department

User = get_user_model()


def create_production_ceo():
    """Create CEO user for production with proper credentials"""
    
    print("🔧 Setting up CEO user for production...")
    
    # CEO details - you can modify these
    ceo_email = input("Enter CEO email (e.g., ceo@yourcompany.com): ").strip()
    if not ceo_email:
        ceo_email = "ceo@company.com"
    
    # Extract username from email
    ceo_username = ceo_email.split('@')[0]
    
    print(f"Using username: {ceo_username}")
    print(f"Using email: {ceo_email}")
    
    # Get password
    ceo_password = input("Enter secure password (leave blank for 'ChangeMe123!'): ").strip()
    if not ceo_password:
        ceo_password = "ChangeMe123!"
    
    # Check if user exists
    if User.objects.filter(username=ceo_username).exists():
        print(f"❌ User with username '{ceo_username}' already exists!")
        return False
    
    if User.objects.filter(email=ceo_email).exists():
        print(f"❌ User with email '{ceo_email}' already exists!")
        return False
    
    # Create Executive department if needed
    executive_dept, created = Department.objects.get_or_create(
        name='Executive',
        defaults={'description': 'Executive leadership team'}
    )
    if created:
        print("✅ Created Executive department")
    
    # Create CEO user
    try:
        ceo_user = User.objects.create_user(
            username=ceo_username,
            email=ceo_email,
            password=ceo_password,
            first_name='Chief',
            last_name='Executive Officer',
            employee_id='CEO001',
            role='ceo',
            department=executive_dept,
            is_staff=True,
            annual_leave_entitlement=30,
            is_active_employee=True
        )
        
        print("\n🎉 SUCCESS! CEO user created!")
        print(f"   👤 Login Email: {ceo_email}")
        print(f"   🔑 Password: {ceo_password}")
        print(f"   🏢 Username: {ceo_username}")
        print(f"   📋 Role: {ceo_user.role}")
        print("\n💡 You can now login to production using the email and password above!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating CEO user: {e}")
        return False


if __name__ == "__main__":
    create_production_ceo()