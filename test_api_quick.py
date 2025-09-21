import requests
import json

# Get a token
token_response = requests.post('http://127.0.0.1:8000/api/auth/token/', json={
    'username': 'john.doe@company.com',
    'password': 'password123'
})

if token_response.status_code == 200:
    token = token_response.json()['access']
    headers = {'Authorization': f'Bearer {token}'}
    
    print("=== Leave Types ===")
    types_response = requests.get('http://127.0.0.1:8000/api/leaves/types/', headers=headers)
    print(f"Status: {types_response.status_code}")
    if types_response.status_code == 200:
        types_data = types_response.json()
        print(json.dumps(types_data, indent=2))
    else:
        print(f"Error: {types_response.text}")
    
    print("\n=== Leave Balances ===")
    balances_response = requests.get('http://127.0.0.1:8000/api/leaves/balances/', headers=headers)
    print(f"Status: {balances_response.status_code}")
    if balances_response.status_code == 200:
        balances_data = balances_response.json()
        print(json.dumps(balances_data, indent=2))
    else:
        print(f"Error: {balances_response.text}")
else:
    print(f"Failed to get token: {token_response.text}")