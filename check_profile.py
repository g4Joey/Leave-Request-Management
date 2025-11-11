#!/usr/bin/env python
import os
import sys
import django

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from users.serializers import UserSerializer

def check_user_profile():
    print("🔍 Check User Profile for Benjamin")
    print("=" * 50)
    
    # Get Benjamin (CEO)
    benjamin = CustomUser.objects.get(email='ceo@umbcapital.com')
    print(f"✅ CEO: {benjamin.username} (ID: {benjamin.id})")
    print(f"   First name: {benjamin.first_name}")
    print(f"   Last name: {benjamin.last_name}")
    print(f"   Email: {benjamin.email}")
    print(f"   Role: {benjamin.role}")
    print(f"   Affiliate: {benjamin.affiliate}")
    print(f"   Is active: {benjamin.is_active}")
    print(f"   Is staff: {benjamin.is_staff}")
    print(f"   Is superuser: {benjamin.is_superuser}")
    
    print()
    print("🔍 UserSerializer Output:")
    serializer = UserSerializer(benjamin)
    data = serializer.data
    
    for key, value in data.items():
        print(f"   {key}: {value}")
    
    print()
    print("🔍 Check if this user should have access to CEO endpoints:")
    print(f"   Role check (role == 'ceo'): {benjamin.role == 'ceo'}")
    print(f"   Superuser check: {benjamin.is_superuser}")
    print(f"   Should pass: {benjamin.role == 'ceo' or benjamin.is_superuser}")

if __name__ == "__main__":
    check_user_profile()