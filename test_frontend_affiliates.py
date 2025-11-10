#!/usr/bin/env python
"""Test the frontend's affiliates endpoint to see what data is returned."""

import os
import sys
import django
import requests

# Setup Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
import json

User = get_user_model()

def test_affiliates_endpoint():
    """Test the /users/affiliates/ endpoint that the frontend uses."""
    print("=== Testing Frontend Affiliates Endpoint ===")
    
    # Create a test client
    client = Client()
    
    # Login as an admin user who should have access
    try:
        # Try to find Benjamin Ackah or any admin user
        admin_user = User.objects.filter(role__in=['admin', 'ceo']).first()
        if not admin_user:
            print("ERROR: No admin or CEO user found for testing")
            return
        
        print(f"Using test user: {admin_user.email} (role: {admin_user.role})")
        
        # Login
        client.force_login(admin_user)
        
        # Test the affiliates endpoint
        print("\n--- Testing /users/affiliates/ endpoint ---")
        response = client.get('/api/users/affiliates/')
        
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {response.status_code}")
            print(f"Response type: {type(data)}")
            
            if isinstance(data, list):
                print(f"Found {len(data)} affiliates")
                for aff in data:
                    print(f"\nAffiliate: {aff.get('name')} (ID: {aff.get('id')})")
                    if 'ceo' in aff:
                        ceo = aff['ceo']
                        if ceo:
                            print(f"  CEO: {ceo.get('name')} ({ceo.get('email')})")
                        else:
                            print(f"  CEO: None")
                    else:
                        print(f"  No CEO field in response")
                    
                    print(f"  All keys: {list(aff.keys())}")
            else:
                print(f"Unexpected response format: {data}")
        else:
            print(f"ERROR {response.status_code}: {response.content.decode()}")
            
    except Exception as e:
        print(f"Error testing affiliates endpoint: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_affiliates_endpoint()