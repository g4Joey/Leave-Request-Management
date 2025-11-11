#!/usr/bin/env python
"""Test affiliate endpoint with direct HTTP request."""

import os
import sys
import django
import requests
import json

# Setup Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

def get_jwt_token():
    """Get a JWT token for testing."""
    # Find an admin user
    admin_user = User.objects.filter(role__in=['admin', 'hr']).first()
    if not admin_user:
        print("No admin user found")
        return None
    
    refresh = RefreshToken.for_user(admin_user)
    return str(refresh.access_token)

def test_api_endpoints():
    """Test the actual API endpoints using HTTP requests."""
    print("=== Testing API Endpoints with HTTP Requests ===")
    
    token = get_jwt_token()
    if not token:
        return
    
    headers = {'Authorization': f'Bearer {token}'}
    base_url = 'http://127.0.0.1:8000/api'
    
    # Test affiliates endpoint
    print("\n1. Testing /users/affiliates/ endpoint:")
    try:
        response = requests.get(f'{base_url}/users/affiliates/', headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            affiliates = response.json()
            print(f"Found {len(affiliates)} affiliates")
            
            for aff in affiliates:
                print(f"\nAffiliate: {aff.get('name')} (ID: {aff.get('id')})")
                if 'ceo' in aff and aff['ceo']:
                    print(f"  CEO Name: '{aff['ceo'].get('name')}'")
                    print(f"  CEO Email: '{aff['ceo'].get('email')}'")
                    print(f"  CEO ID: {aff['ceo'].get('id')}")
                else:
                    print(f"  CEO: None or missing")
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    
    # Test MERBAN staff endpoint  
    print("\n2. Testing /users/staff/?affiliate_id=1 endpoint:")
    try:
        response = requests.get(f'{base_url}/users/staff/?affiliate_id=1', headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            staff_data = response.json()
            print(f"Staff data type: {type(staff_data)}")
            
            if isinstance(staff_data, list):
                print(f"Found {len(staff_data)} items")
                for item in staff_data:
                    if isinstance(item, dict) and 'staff' in item:
                        dept_name = item.get('name', 'Unknown')
                        staff_list = item.get('staff', [])
                        print(f"  Department '{dept_name}': {len(staff_list)} staff")
                        for staff in staff_list:
                            if staff.get('role') == 'ceo':
                                print(f"    CEO: {staff.get('name')} ({staff.get('email')})")
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_api_endpoints()