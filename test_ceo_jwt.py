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

from rest_framework_simplejwt.tokens import RefreshToken
from users.models import CustomUser
import requests
import json

def get_jwt_token_for_user(user):
    """Get a JWT token for a specific user"""
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)

def test_ceo_endpoint_with_jwt():
    print("🔍 Test CEO Endpoint with JWT Authentication")
    print("=" * 60)
    
    # Get Benjamin (CEO)
    benjamin = CustomUser.objects.get(email='ceo@umbcapital.com')
    print(f"✅ CEO: {benjamin.username} ({benjamin.email})")
    print(f"   Role: {benjamin.role}")
    print(f"   Affiliate: {benjamin.affiliate}")
    
    # Get JWT token
    jwt_token = get_jwt_token_for_user(benjamin)
    print(f"   JWT Token: {jwt_token[:50]}...")
    
    # Test with actual HTTP requests (like frontend does)
    base_url = "http://localhost:8000"  # Adjust if different
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Content-Type': 'application/json'
    }
    
    print()
    print("🔍 Test 1: CEO Approvals Categorized Endpoint")
    try:
        response = requests.get(f"{base_url}/leaves/manager/ceo_approvals_categorized/", headers=headers)
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
                print(f"   ❌ ISSUE: No requests found (total_count: {data.get('total_count')})")
                print(f"   Full response: {json.dumps(data, indent=2)}")
                
        elif response.status_code == 403:
            print(f"   ❌ Forbidden: {response.json()}")
        elif response.status_code == 401:
            print(f"   ❌ Unauthorized: {response.json()}")
        else:
            print(f"   ❌ Error {response.status_code}: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection Error: Is the Django server running on localhost:8000?")
        print("   💡 Suggestion: Run 'python manage.py runserver' in another terminal")
        return
    except Exception as e:
        print(f"   Exception: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("🔍 Test 2: Check Base Manager Endpoint")
    try:
        response = requests.get(f"{base_url}/leaves/manager/", headers=headers)
        print(f"   Base endpoint status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Base endpoint count: {data.get('count', 'Not found')}")
            results = data.get('results', [])
            print(f"   Results: {len(results)} requests")
            if results:
                print(f"   First result: ID {results[0].get('id')} - {results[0].get('employee_name')} (status: {results[0].get('status')})")
    except Exception as e:
        print(f"   Base endpoint error: {e}")

if __name__ == "__main__":
    test_ceo_endpoint_with_jwt()