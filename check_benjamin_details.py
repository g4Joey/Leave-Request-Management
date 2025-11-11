#!/usr/bin/env python
"""Check Benjamin Ackah's full name in the database."""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser as User

def check_benjamin_details():
    print("=== Checking Benjamin Ackah's Details ===")
    
    try:
        # Find Benjamin Ackah
        benjamin = User.objects.filter(email='ceo@umbcapital.com').first()
        
        if not benjamin:
            print("Benjamin Ackah not found!")
            return
        
        print(f"User found: {benjamin.email}")
        print(f"ID: {benjamin.id}")
        print(f"Username: {benjamin.username}")
        print(f"First Name: '{benjamin.first_name}'")
        print(f"Last Name: '{benjamin.last_name}'")
        print(f"get_full_name(): '{benjamin.get_full_name()}'")
        print(f"get_full_name().strip(): '{benjamin.get_full_name().strip()}'")
        print(f"Role: {benjamin.role}")
        print(f"Affiliate: {benjamin.affiliate}")
        print(f"Department: {benjamin.department}")
        print(f"Is Active: {benjamin.is_active}")
        
        # Test the AffiliateSerializer get_ceo method
        from users.serializers import AffiliateSerializer
        if benjamin.affiliate:
            print(f"\n--- Testing AffiliateSerializer.get_ceo() for {benjamin.affiliate.name} ---")
            serializer = AffiliateSerializer()
            ceo_data = serializer.get_ceo(benjamin.affiliate)
            print(f"CEO data returned: {ceo_data}")
            
            if ceo_data:
                print(f"  Name: '{ceo_data.get('name')}'")
                print(f"  Email: '{ceo_data.get('email')}'")
                print(f"  ID: {ceo_data.get('id')}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_benjamin_details()