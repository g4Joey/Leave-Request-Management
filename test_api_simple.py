import requests
import json

# Test API endpoints
base_url = "http://172.20.10.2:8000/api"

# Login to get token
login_data = {
    "username": "john.doe@company.com",
    "password": "password123"
}

login_response = requests.post(f"{base_url}/auth/login/", json=login_data)
token = login_response.json()["access"]

headers = {"Authorization": f"Bearer {token}"}

# Test leave types
types_response = requests.get(f"{base_url}/leaves/types/", headers=headers)
print("=== Leave Types ===")
print(f"Status: {types_response.status_code}")
if types_response.status_code == 200:
    types_data = types_response.json()
    print(json.dumps(types_data, indent=2))
else:
    print(f"Error: {types_response.text}")