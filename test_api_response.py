#!/usr/bin/env python
import requests
import json

# Test the actual API endpoint
api_url = "http://localhost:8000/leaves/balances/current_year_full/"

# Use the admin user credentials  
login_data = {
    'username': 'admin@company.com',
    'password': 'admin123'
}

# Login to get token
login_response = requests.post('http://localhost:8000/api/auth/login/', data=login_data)
if login_response.status_code == 200:
    token = login_response.json().get('access')
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get balances
    response = requests.get(api_url, headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("=== ACTUAL API RESPONSE STRUCTURE ===")
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {response.text}")
else:
    print(f"Login failed: {login_response.text}")