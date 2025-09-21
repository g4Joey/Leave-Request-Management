#!/usr/bin/env python3
"""Quick test script to verify API endpoints and auth token"""
import requests
import json

BASE_URL = "http://172.20.10.2:8000/api"

def test_auth_and_data():
    print("🔍 Testing Authentication and Data APIs")
    print("=" * 50)
    
    # 1. Test authentication
    print("\n1. Testing login...")
    auth_data = {
        "username": "john.doe@company.com",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/token/", json=auth_data)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            tokens = response.json()
            access_token = tokens.get('access')
            print("   ✅ Login successful")
            
            # Headers for authenticated requests
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # 2. Test leave types endpoint
            print("\n2. Testing leave types...")
            types_response = requests.get(f"{BASE_URL}/leaves/types/", headers=headers)
            print(f"   Status: {types_response.status_code}")
            if types_response.status_code == 200:
                types_data = types_response.json()
                print(f"   ✅ Found {len(types_data.get('results', types_data))} leave types")
                for lt in types_data.get('results', types_data)[:3]:  # Show first 3
                    print(f"     - {lt.get('name', 'N/A')}: {lt.get('description', 'No desc')}")
            else:
                print(f"   ❌ Error: {types_response.text}")
            
            # 3. Test leave balances endpoint  
            print("\n3. Testing leave balances...")
            balances_response = requests.get(f"{BASE_URL}/leaves/balances/", headers=headers)
            print(f"   Status: {balances_response.status_code}")
            if balances_response.status_code == 200:
                balances_data = balances_response.json()
                balances = balances_data.get('results', balances_data)
                print(f"   ✅ Found {len(balances)} leave balances")
                for balance in balances[:3]:  # Show first 3
                    lt_name = balance.get('leave_type_name', 'NO NAME')
                    entitled = balance.get('entitled_days', 0)
                    remaining = balance.get('remaining_days', 0)
                    print(f"     - {lt_name}: {remaining} of {entitled} days remaining")
            else:
                print(f"   ❌ Error: {balances_response.text}")
                
        else:
            print(f"   ❌ Login failed: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection failed - is Django server running?")
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_auth_and_data()