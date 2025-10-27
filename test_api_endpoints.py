#!/usr/bin/env python
"""
Quick API test to verify endpoints are accessible
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

import requests
from users.models import CustomUser
from rest_framework_simplejwt.tokens import RefreshToken

def test_api_endpoints():
    print("=== TESTING API ENDPOINTS ===")
    
    # Get a user and generate token
    user = CustomUser.objects.filter(is_active=True).first()
    if not user:
        print("No active user found!")
        return
    
    token = str(RefreshToken.for_user(user).access_token)
    headers = {'Authorization': f'Bearer {token}'}
    base_url = 'http://127.0.0.1:8000/api'
    
    print(f"Testing with user: {user.username}")
    print(f"Token: {token[:20]}...")
    
    # Test balances endpoint
    try:
        response = requests.get(f'{base_url}/leaves/balances/current_year_full/', headers=headers)
        print(f"Balances endpoint: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Data length: {len(data)}")
            if data:
                print(f"  First item: {data[0]}")
        else:
            print(f"  Error: {response.text}")
    except Exception as e:
        print(f"  Exception: {e}")
    
    # Test requests endpoint
    try:
        response = requests.get(f'{base_url}/leaves/requests/?limit=5', headers=headers)
        print(f"Requests endpoint: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Data type: {type(data)}")
            if isinstance(data, dict) and 'results' in data:
                print(f"  Results length: {len(data['results'])}")
            elif isinstance(data, list):
                print(f"  List length: {len(data)}")
        else:
            print(f"  Error: {response.text}")
    except Exception as e:
        print(f"  Exception: {e}")
    
    # Test admin reset endpoint (with admin user)
    admin_user = CustomUser.objects.filter(is_superuser=True).first()
    if admin_user:
        admin_token = str(RefreshToken.for_user(admin_user).access_token)
        admin_headers = {'Authorization': f'Bearer {admin_token}', 'Content-Type': 'application/json'}
        
        try:
            response = requests.post(f'{base_url}/leaves/manager/system_reset/', 
                                   json={'confirm_reset': 'yes, reset everything'}, 
                                   headers=admin_headers)
            print(f"Admin reset endpoint: {response.status_code}")
            if response.status_code == 200:
                print(f"  Reset successful: {response.json()}")
            else:
                print(f"  Error: {response.text}")
        except Exception as e:
            print(f"  Exception: {e}")

if __name__ == "__main__":
    test_api_endpoints()