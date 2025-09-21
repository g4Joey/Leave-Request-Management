import requests
import json

# Test leave types endpoint specifically
base_url = "http://172.20.10.2:8000/api"

# Login to get token
login_data = {
    "username": "john.doe@company.com",
    "password": "password123"
}

try:
    login_response = requests.post(f"{base_url}/auth/token/", json=login_data)
    if login_response.status_code == 200:
        token = login_response.json()["access"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test leave types for dropdown
        types_response = requests.get(f"{base_url}/leaves/types/", headers=headers)
        if types_response.status_code == 200:
            types_data = types_response.json()
            print("=== Leave Types for Dropdown ===")
            print(f"Response structure: {types_data.keys() if isinstance(types_data, dict) else 'Array'}")
            
            # Handle both paginated and non-paginated responses
            types_list = types_data.get('results', types_data) if isinstance(types_data, dict) else types_data
            
            print(f"Number of types: {len(types_list)}")
            for i, leave_type in enumerate(types_list):
                print(f"  {i+1}. ID: {leave_type['id']}, Name: '{leave_type['name']}'")
        else:
            print(f"Error: {types_response.status_code}")
            print(types_response.text)
    else:
        print(f"Login failed: {login_response.status_code}")
        
except Exception as e:
    print(f"Error: {e}")