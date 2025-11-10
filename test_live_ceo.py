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

from django.test.client import Client
from django.contrib.auth import get_user_model
from users.models import CustomUser
import json

def test_live_ceo_endpoint():
    print("🔍 Test Live CEO Endpoint (like frontend)")
    print("=" * 50)
    
    # Get Benjamin
    benjamin = CustomUser.objects.get(email='ceo@umbcapital.com')
    print(f"✅ CEO: {benjamin.username} ({benjamin.email})")
    
    # Create a test client
    client = Client()
    
    # Login as Benjamin
    login_success = client.force_login(benjamin)
    print(f"   Force login result: {login_success}")
    
    print()
    print("🔍 Test 1: GET /leaves/manager/ceo_approvals_categorized/")
    
    try:
        response = client.get('/leaves/manager/ceo_approvals_categorized/')
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   Response type: {type(data)}")
                print(f"   Total count: {data.get('total_count', 'Not found')}")
                
                categories = data.get('categories', {})
                counts = data.get('counts', {})
                print(f"   Categories: {list(categories.keys())}")
                print(f"   Counts: {counts}")
                
                if data.get('total_count', 0) > 0:
                    print(f"   ✅ Found {data['total_count']} request(s)")
                    for category, requests in categories.items():
                        if requests:
                            print(f"   📋 {category.upper()}: {len(requests)} requests")
                            for req in requests[:2]:  # Show first 2
                                print(f"       • ID {req.get('id')}: {req.get('employee_name')} (status: {req.get('status')})")
                else:
                    print(f"   ⚠️  No requests returned (total_count: {data.get('total_count')})")
                    
            except json.JSONDecodeError:
                print(f"   Response content (non-JSON): {response.content[:200]}")
        elif response.status_code == 403:
            print(f"   ❌ Forbidden: {response.json()}")
        elif response.status_code == 401:
            print(f"   ❌ Unauthorized: {response.json()}")
        else:
            print(f"   ❌ Error {response.status_code}: {response.content[:200]}")
            
    except Exception as e:
        print(f"   Exception: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("🔍 Test 2: Check if user is properly authenticated in session")
    try:
        response = client.get('/api/profile/')  # Assuming there's a profile endpoint
        print(f"   Profile endpoint status: {response.status_code}")
        if response.status_code == 200:
            profile_data = response.json()
            print(f"   Profile user: {profile_data.get('username')} ({profile_data.get('email')})")
            print(f"   Profile role: {profile_data.get('role')}")
    except Exception as e:
        print(f"   Profile check failed: {e}")
    
    print()
    print("🔍 Test 3: Try the base manager endpoint")
    try:
        response = client.get('/leaves/manager/')
        print(f"   Base manager endpoint status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Base endpoint count: {data.get('count', 'Not found')}")
            results = data.get('results', [])
            print(f"   Results count: {len(results)}")
            if results:
                print(f"   First result: ID {results[0].get('id')} - {results[0].get('employee_name')}")
    except Exception as e:
        print(f"   Base endpoint error: {e}")

if __name__ == "__main__":
    test_live_ceo_endpoint()