import requests
import json

# Test API endpoints
base_url = "http://172.20.10.2:8000/api"

# Login to get token - corrected endpoint
login_data = {
    "username": "john.doe@company.com",
    "password": "password123"
}

print("Attempting login...")
try:
    login_response = requests.post(f"{base_url}/auth/token/", json=login_data)
    print(f"Login status: {login_response.status_code}")
    
    if login_response.status_code == 200:
        token = login_response.json()["access"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Login successful!")
        
        # Test leave types
        print("\n=== Testing Leave Types ===")
        types_response = requests.get(f"{base_url}/leaves/types/", headers=headers)
        print(f"Status: {types_response.status_code}")
        if types_response.status_code == 200:
            types_data = types_response.json()
            print("Leave Types Data:")
            print(json.dumps(types_data, indent=2))
        else:
            print(f"Error response: {types_response.text}")
        
    else:
        print(f"Login failed: {login_response.text}")
        
except Exception as e:
    print(f"Error: {e}")