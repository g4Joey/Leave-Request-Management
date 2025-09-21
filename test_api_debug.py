import requests
import json

# Test API endpoints
base_url = "http://172.20.10.2:8000/api"

# Login to get token
login_data = {
    "username": "john.doe@company.com",
    "password": "password123"
}

print("Attempting login...")
try:
    login_response = requests.post(f"{base_url}/auth/login/", json=login_data)
    print(f"Login status: {login_response.status_code}")
    print(f"Login response: {login_response.text}")
    
    if login_response.status_code == 200:
        token = login_response.json()["access"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test leave types
        print("\n=== Testing Leave Types ===")
        types_response = requests.get(f"{base_url}/leaves/types/", headers=headers)
        print(f"Status: {types_response.status_code}")
        print(f"Response: {types_response.text}")
        
    else:
        print("Login failed")
        
except Exception as e:
    print(f"Error: {e}")