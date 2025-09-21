import requests
import json

# Test API endpoints after fixing frontend
base_url = "http://172.20.10.2:8000/api"

# Login to get token
login_data = {
    "username": "john.doe@company.com",
    "password": "password123"
}

try:
    print("=== Testing API Endpoints ===")
    
    # Login
    login_response = requests.post(f"{base_url}/auth/token/", json=login_data)
    if login_response.status_code == 200:
        token = login_response.json()["access"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✓ Login successful")
        
        # Test leave types
        types_response = requests.get(f"{base_url}/leaves/types/", headers=headers)
        if types_response.status_code == 200:
            types_data = types_response.json()
            print(f"✓ Leave Types: {len(types_data.get('results', types_data))} types found")
            
            # Print first type structure
            first_type = types_data.get('results', types_data)[0] if types_data else None
            if first_type:
                print(f"  Sample: {first_type}")
        
        # Test leave balances
        balances_response = requests.get(f"{base_url}/leaves/balances/", headers=headers)
        if balances_response.status_code == 200:
            balances_data = balances_response.json()
            print(f"✓ Leave Balances: {len(balances_data.get('results', []))} balances found")
            
            # Print first balance structure
            first_balance = balances_data.get('results', [])[0] if balances_data.get('results') else None
            if first_balance:
                print(f"  Sample: has 'leave_type_name': {'leave_type_name' in first_balance}")
                print(f"  leave_type_name value: {first_balance.get('leave_type_name', 'NOT FOUND')}")
        
    else:
        print(f"✗ Login failed: {login_response.status_code}")
        
except Exception as e:
    print(f"✗ Error: {e}")