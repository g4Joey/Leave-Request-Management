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

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from users.models import CustomUser
import json

def get_jwt_token_for_user(user):
    """Get a JWT token for a specific user"""
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)

def test_ceo_endpoint_properly():
    print("🔍 Test CEO Endpoint with Proper JWT Authentication")
    print("=" * 60)
    
    # Get Benjamin (CEO)
    benjamin = CustomUser.objects.get(email='ceo@umbcapital.com')
    print(f"✅ CEO: {benjamin.username} ({benjamin.email})")
    print(f"   Role: {benjamin.role}")
    print(f"   Affiliate: {benjamin.affiliate}")
    
    # Create API client and authenticate
    client = APIClient()
    
    # Method 1: Use force_authenticate
    print()
    print("🔍 Method 1: Using force_authenticate")
    client.force_authenticate(user=benjamin)
    
    try:
    response = client.get('/leaves/ceo/approvals_categorized/')
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Total Count: {data.get('total_count', 'Not found')}")
            
            categories = data.get('categories', {})
            counts = data.get('counts', {})
            print(f"   Counts: {counts}")
            
            if data.get('total_count', 0) > 0:
                print(f"   ✅ SUCCESS: Found {data['total_count']} request(s)")
                for category, requests in categories.items():
                    if requests:
                        print(f"   📋 {category.upper()}: {len(requests)} requests")
                        for req in requests:
                            print(f"       • ID {req.get('id')}: {req.get('employee_name')} ({req.get('employee_email')})")
                            print(f"         Status: {req.get('status')}, Role: {req.get('employee_role')}")
            else:
                print(f"   ⚠️  No requests found (total_count: {data.get('total_count')})")
                print(f"   Categories structure: {list(categories.keys())}")
                
        elif response.status_code == 403:
            error_data = response.json() if response.content else {'detail': 'No content'}
            print(f"   ❌ Forbidden: {error_data}")
        elif response.status_code == 401:
            error_data = response.json() if response.content else {'detail': 'No content'}
            print(f"   ❌ Unauthorized: {error_data}")
        else:
            print(f"   ❌ Error {response.status_code}: {response.content}")
            
    except Exception as e:
        print(f"   Exception: {e}")
        import traceback
        traceback.print_exc()
    
    # Method 2: Use JWT token
    print()
    print("🔍 Method 2: Using JWT Token")
    client2 = APIClient()
    jwt_token = get_jwt_token_for_user(benjamin)
    client2.credentials(HTTP_AUTHORIZATION=f'Bearer {jwt_token}')
    
    try:
    response2 = client2.get('/leaves/ceo/approvals_categorized/')
        print(f"   Status Code: {response2.status_code}")
        
        if response2.status_code == 200:
            data2 = response2.json()
            print(f"   Total Count: {data2.get('total_count', 'Not found')}")
            counts2 = data2.get('counts', {})
            print(f"   Counts: {counts2}")
            
            if data2.get('total_count', 0) > 0:
                print(f"   ✅ SUCCESS with JWT: Found {data2['total_count']} request(s)")
            else:
                print(f"   ⚠️  No requests with JWT either")
        else:
            error_data2 = response2.json() if response2.content else {'detail': 'No content'}
            print(f"   ❌ JWT Error {response2.status_code}: {error_data2}")
            
    except Exception as e:
        print(f"   JWT Exception: {e}")
    
    # Test base manager endpoint for comparison
    print()
    print("🔍 Test 3: Base Manager Endpoint for comparison")
    try:
        response3 = client.get('/leaves/manager/')
        print(f"   Base endpoint status: {response3.status_code}")
        if response3.status_code == 200:
            data3 = response3.json()
            print(f"   Base endpoint count: {data3.get('count', 'Not found')}")
            results = data3.get('results', [])
            print(f"   Base results: {len(results)} requests")
            if results:
                for i, req in enumerate(results[:3]):  # Show first 3
                    print(f"       {i+1}. ID {req.get('id')}: {req.get('employee_name')} (status: {req.get('status')})")
    except Exception as e:
        print(f"   Base endpoint error: {e}")

if __name__ == "__main__":
    test_ceo_endpoint_properly()