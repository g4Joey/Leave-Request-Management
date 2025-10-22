#!/usr/bin/env python
"""
Script to update existing 'manager' role users to 'hod' role in the database.
This should be run after the migration to ensure all existing manager users are updated to the new role.
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.db import transaction
from users.models import CustomUser


def update_manager_roles():
    """Update all users with 'manager' role to 'hod' role."""
    try:
        with transaction.atomic():
            # Find all users with 'manager' role
            manager_users = CustomUser.objects.filter(role='manager')
            count = manager_users.count()
            
            if count == 0:
                print("✅ No users with 'manager' role found. All users already updated or no manager users exist.")
                return
            
            print(f"📋 Found {count} users with 'manager' role:")
            for user in manager_users:
                print(f"  - {user.username} ({user.get_full_name()}) - Employee ID: {user.employee_id}")
            
            # Update all manager users to hod
            updated = manager_users.update(role='hod')
            
            print(f"\n✅ Successfully updated {updated} users from 'manager' role to 'hod' role.")
            
            # Verify the update
            remaining_managers = CustomUser.objects.filter(role='manager').count()
            new_hods = CustomUser.objects.filter(role='hod').count()
            
            print(f"📊 Verification:")
            print(f"  - Remaining 'manager' role users: {remaining_managers}")
            print(f"  - Total 'hod' role users: {new_hods}")
            
    except Exception as e:
        print(f"❌ Error updating manager roles: {e}")
        return False
    
    return True


def main():
    print("🔄 Starting Manager → HOD Role Update Process")
    print("=" * 50)
    
    # Check current role distribution
    print("📈 Current role distribution:")
    roles = CustomUser.objects.values_list('role', flat=True).distinct()
    for role in sorted(roles):
        count = CustomUser.objects.filter(role=role).count()
        print(f"  - {role}: {count} users")
    
    print("\n" + "=" * 50)
    
    # Perform the update
    success = update_manager_roles()
    
    if success:
        print("\n📈 Updated role distribution:")
        roles = CustomUser.objects.values_list('role', flat=True).distinct()
        for role in sorted(roles):
            count = CustomUser.objects.filter(role=role).count()
            print(f"  - {role}: {count} users")
        
        print("\n🎉 Role update completed successfully!")
        print("💡 The system has been updated to use 'HOD' (Head of Department) instead of 'Manager'")
    else:
        print("\n❌ Role update failed. Please check the error messages above.")


if __name__ == '__main__':
    main()