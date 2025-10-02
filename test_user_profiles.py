#!/usr/bin/env python3
"""
Test script to check user profile data and roles
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.serializers import UserSerializer

def test_user_profile_data():
    print("=== Testing User Profile Data ===")
    
    User = get_user_model()
    
    # Get all users and their serialized data
    users = User.objects.all()
    print(f"Total users in database: {users.count()}")
    
    for user in users:
        print(f"\n--- User: {user.username} ---")
        print(f"  ID: {user.id}")
        print(f"  Email: {user.email}")
        print(f"  First Name: {user.first_name}")
        print(f"  Last Name: {user.last_name}")
        print(f"  Role: {user.role}")
        print(f"  is_superuser: {user.is_superuser}")
        print(f"  is_staff: {user.is_staff}")
        print(f"  is_active: {user.is_active}")
        
        # Test serialization
        try:
            serializer = UserSerializer(user)
            serialized_data = serializer.data
            print(f"  Serialized role: {serialized_data.get('role')}")
            print(f"  Serialized is_superuser: {serialized_data.get('is_superuser')}")
            
            # Check navigation conditions
            can_see_manager = serialized_data.get('role') == 'manager' or serialized_data.get('is_superuser')
            can_see_staff = serialized_data.get('role') == 'hr' or serialized_data.get('is_superuser')
            
            print(f"  Should see Manager tab: {can_see_manager}")
            print(f"  Should see Staff tab: {can_see_staff}")
            
        except Exception as e:
            print(f"  Serialization error: {e}")

if __name__ == '__main__':
    test_user_profile_data()