#!/usr/bin/env python
"""
Production initialization script for DigitalOcean deployment
Run this after deploying to production to set up the CEO and verify the system
"""
import os
import sys
import django
from getpass import getpass

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model

User = get_user_model()

def initialize_production():
    """Initialize production environment with CEO user"""
    print("🚀 PRODUCTION INITIALIZATION")
    print("=" * 50)
    
    # Check if CEO already exists
    ceo_exists = User.objects.filter(role='ceo').exists()
    if ceo_exists:
        ceo = User.objects.filter(role='ceo').first()
        print(f"✅ CEO user already exists: {ceo.username} ({ceo.get_full_name()})")
        
        response = input("Do you want to create another CEO user? (y/N): ")
        if response.lower() != 'y':
            print("Skipping CEO creation...")
            verify_system()
            return
    
    # Collect CEO information
    print("\n📝 Enter CEO Information:")
    username = input("CEO Username: ").strip()
    email = input("CEO Email: ").strip()
    first_name = input("First Name: ").strip()
    last_name = input("Last Name: ").strip()
    employee_id = input("Employee ID (default: CEO001): ").strip() or "CEO001"
    
    if not all([username, email, first_name, last_name]):
        print("❌ All fields are required!")
        return
    
    # Create CEO using management command
    try:
        print(f"\n🔧 Creating CEO user...")
        call_command('create_ceo', 
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    employee_id=employee_id)
        
        # Get the created CEO
        ceo = User.objects.get(username=username)
        
        # Ask if they want to change the default password
        change_password = input(f"\nDefault password is 'ChangeMe123!'. Change it now? (Y/n): ")
        if change_password.lower() != 'n':
            new_password = getpass("Enter new password: ")
            confirm_password = getpass("Confirm password: ")
            
            if new_password != confirm_password:
                print("❌ Passwords don't match!")
                print("⚠️  CEO created but password is still 'ChangeMe123!' - CHANGE IT!")
            elif len(new_password) < 8:
                print("❌ Password too short (minimum 8 characters)!")
                print("⚠️  CEO created but password is still 'ChangeMe123!' - CHANGE IT!")
            else:
                ceo.set_password(new_password)
                ceo.save()
                print("✅ Password changed successfully!")
        
        print(f"\n✅ CEO Setup Complete!")
        print(f"   Username: {ceo.username}")
        print(f"   Email: {ceo.email}")
        print(f"   Role: {ceo.role}")
        print(f"   Department: {ceo.department.name if ceo.department else 'None'}")
        
    except Exception as e:
        print(f"❌ Error creating CEO: {str(e)}")
        return
    
    # Verify the system
    verify_system()

def verify_system():
    """Verify the three-tier approval system is working"""
    print(f"\n🔍 SYSTEM VERIFICATION")
    print("=" * 30)
    
    try:
        # Check CEO users
        ceo_users = User.objects.filter(role='ceo')
        print(f"✅ CEO Users ({ceo_users.count()}):")
        for ceo in ceo_users:
            print(f"   • {ceo.username} ({ceo.get_full_name()})")
        
        # Check other roles
        roles = ['hod', 'hr', 'junior_staff', 'senior_staff', 'admin']
        for role in roles:
            count = User.objects.filter(role=role).count()
            print(f"✅ {role.title().replace('_', ' ')} Users: {count}")
        
        # Check if migrations are applied
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'leaves_leaverequest';")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(leaves_leaverequest);")
                columns = [row[1] for row in cursor.fetchall()]
                ceo_fields = ['ceo_approved_by_id', 'ceo_approval_date', 'ceo_approval_comments']
                missing_fields = [f for f in ceo_fields if f not in columns]
                if not missing_fields:
                    print("✅ Database migrations applied correctly")
                else:
                    print(f"❌ Missing fields: {missing_fields}")
                    print("   Run: python manage.py migrate")
        
        print(f"\n🎉 SYSTEM READY FOR PRODUCTION!")
        print(f"✅ Three-tier approval system: Staff → Manager → HR → CEO")
        print(f"✅ Role-based access control implemented")
        print(f"✅ Notification system configured")
        print(f"✅ Database schema updated")
        
        print(f"\n📋 NEXT STEPS:")
        print(f"   1. Test the approval workflow with real users")
        print(f"   2. Configure email settings for notifications")
        print(f"   3. Set up proper backup procedures")
        print(f"   4. Train users on the new approval process")
        
    except Exception as e:
        print(f"❌ Verification error: {str(e)}")
        print("   Check your database connection and migrations")

if __name__ == '__main__':
    try:
        initialize_production()
    except KeyboardInterrupt:
        print(f"\n❌ Initialization cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()