#!/usr/bin/env python3
"""
Test script to check media file serving and profile image paths
"""
import os
import django
import sys
from pathlib import Path

# Setup Django environment
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.conf import settings
from users.models import CustomUser

def test_media_setup():
    """Test media file configuration and profile images"""
    print("🔍 Testing Media File Configuration")
    print("=" * 50)
    
    print(f"📁 MEDIA_URL: {getattr(settings, 'MEDIA_URL', 'NOT SET')}")
    print(f"📁 MEDIA_ROOT: {getattr(settings, 'MEDIA_ROOT', 'NOT SET')}")
    
    if hasattr(settings, 'MEDIA_ROOT'):
        media_root = Path(settings.MEDIA_ROOT)
        print(f"📁 MEDIA_ROOT exists: {media_root.exists()}")
        
        profiles_dir = media_root / 'profiles'
        print(f"📁 Profiles directory exists: {profiles_dir.exists()}")
        
        if profiles_dir.exists():
            profile_files = list(profiles_dir.glob('*'))
            print(f"📁 Profile files found: {len(profile_files)}")
            for file in profile_files[:5]:  # Show first 5 files
                print(f"   - {file.name} ({file.stat().st_size} bytes)")
    
    print("\n👤 User Profile Images:")
    print("-" * 30)
    
    users_with_images = CustomUser.objects.exclude(profile_image='').exclude(profile_image__isnull=True)
    print(f"Users with profile images: {users_with_images.count()}")
    
    for user in users_with_images[:5]:  # Show first 5 users
        print(f"   {user.email}: {user.profile_image}")
        if user.profile_image:
            full_path = Path(settings.MEDIA_ROOT) / user.profile_image.name
            print(f"      File exists: {full_path.exists()}")
            if full_path.exists():
                print(f"      File size: {full_path.stat().st_size} bytes")

if __name__ == '__main__':
    test_media_setup()