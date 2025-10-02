#!/usr/bin/env python3
"""
Test script for profile updates to help debug the issues
"""
import os
import django
import sys

# Setup Django environment
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from users.serializers import UserSerializer

def test_profile_update():
    """Test profile update functionality"""
    print("🔍 Testing Profile Update Functionality")
    print("=" * 50)
    
    # Get a test user
    user = CustomUser.objects.first()
    if not user:
        print("❌ No users found in database")
        return
    
    print(f"📋 Testing with user: {user.email}")
    print(f"   Current name: {user.first_name} {user.last_name}")
    print(f"   Current phone: {user.phone}")
    print(f"   Employee ID: {user.employee_id}")
    
    # Test serializer validation with typical profile update data
    test_data = {
        'first_name': user.first_name or 'Test',
        'last_name': user.last_name or 'User', 
        'email': user.email,
        'phone': '123-456-7890'
    }
    
    print(f"\n🧪 Testing serializer with data: {test_data}")
    
    serializer = UserSerializer(user, data=test_data, partial=True)
    
    if serializer.is_valid():
        print("✅ Serializer validation passed")
        # Don't actually save, just test validation
        print(f"   Validated data: {serializer.validated_data}")
    else:
        print("❌ Serializer validation failed")
        print(f"   Errors: {serializer.errors}")
    
    # Test with empty/minimal data
    minimal_data = {
        'first_name': 'Updated',
        'last_name': 'Name'
    }
    
    print(f"\n🧪 Testing serializer with minimal data: {minimal_data}")
    
    serializer2 = UserSerializer(user, data=minimal_data, partial=True)
    
    if serializer2.is_valid():
        print("✅ Minimal data validation passed")
        print(f"   Validated data: {serializer2.validated_data}")
    else:
        print("❌ Minimal data validation failed")
        print(f"   Errors: {serializer2.errors}")

if __name__ == '__main__':
    test_profile_update()