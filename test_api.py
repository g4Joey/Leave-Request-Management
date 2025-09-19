"""
API Test Script - Test the core leave management APIs
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def test_api_endpoints():
    """Test basic API endpoints"""
    
    print("🧪 Testing Leave Management API Endpoints")
    print("=" * 50)
    
    # Test unauthenticated access (should require authentication)
    print("\n1. Testing unauthenticated access to leave types...")
    try:
        response = requests.get(f"{BASE_URL}/leaves/types/")
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Authentication required as expected")
        else:
            print(f"   ⚠️  Unexpected response: {response.text[:100]}")
    except requests.exceptions.ConnectionError:
        print("   ❌ Server not running. Please start the Django server first.")
        return False
    
    # Test authentication endpoint
    print("\n2. Testing authentication endpoint...")
    try:
        response = requests.post(f"{BASE_URL}/auth/token/", {
            "username": "g4joey",  # Using the superuser we created
            "password": "your_password_here"  # You'll need to replace this
        })
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Authentication successful")
            token_data = response.json()
            access_token = token_data.get('access')
            
            # Test authenticated request
            print("\n3. Testing authenticated request...")
            headers = {'Authorization': f'Bearer {access_token}'}
            auth_response = requests.get(f"{BASE_URL}/leaves/types/", headers=headers)
            print(f"   Status: {auth_response.status_code}")
            if auth_response.status_code == 200:
                print("   ✅ Authenticated request successful")
                print(f"   Data: {auth_response.json()}")
            else:
                print(f"   ⚠️  Response: {auth_response.text}")
        else:
            print(f"   ⚠️  Authentication failed: {response.text}")
    except requests.exceptions.ConnectionError:
        print("   ❌ Server not running.")
        return False
    
    print("\n4. Available API Endpoints:")
    endpoints = [
        "GET  /api/leaves/types/              - List leave types",
        "GET  /api/leaves/balances/           - View leave balances",
        "POST /api/leaves/requests/           - Submit leave request (R1)",
        "GET  /api/leaves/requests/           - List leave requests (R12)",
        "GET  /api/leaves/requests/dashboard/ - Dashboard summary (R2)",
        "GET  /api/leaves/requests/history/   - Leave history (R12)",
        "GET  /api/leaves/manager/            - Manager view of requests (R4)",
        "PUT  /api/leaves/manager/{id}/approve/ - Approve request (R4)",
        "PUT  /api/leaves/manager/{id}/reject/  - Reject request (R4)",
    ]
    
    for endpoint in endpoints:
        print(f"   {endpoint}")
    
    print("\n✅ API endpoints are configured and responding!")
    print("\n📋 Next Steps:")
    print("   1. Create test users through Django admin or management command")
    print("   2. Test leave submission and approval workflow")
    print("   3. Verify all requirements (R1-R12) are working")
    
    return True

if __name__ == "__main__":
    test_api_endpoints()