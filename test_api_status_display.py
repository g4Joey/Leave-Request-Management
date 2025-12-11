import os
import django
import requests
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

# Login as HR
login_url = "http://127.0.0.1:8000/api/login/"
hr_credentials = {
    "email": "hradmin@umbcapital.com",
    "password": "1HRADMIN"
}

print("Testing HR Approval Records API with Dynamic Status")
print("=" * 70)

# Login
response = requests.post(login_url, json=hr_credentials)
if response.status_code == 200:
    token = response.json()['access']
    headers = {'Authorization': f'Bearer {token}'}
    
    # Fetch approval records
    url = "http://127.0.0.1:8000/api/leave-requests/approval_records/"
    print(f"\nFetching: {url}")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total records: {data.get('count', 0)}")
        
        # Display first 5 records with status info
        records = data.get('results', [])[:5]
        print(f"\nShowing first {len(records)} records:")
        print("-" * 70)
        
        for record in records:
            print(f"\nLR#{record['id']} - {record['employee_name']}")
            print(f"  Status (raw): {record['status']}")
            print(f"  Status Display: {record.get('status_display', 'N/A')}")
            print(f"  Affiliate: {record.get('employee_department_affiliate', 'N/A')}")
            print(f"  Leave Type: {record['leave_type_name']}")
    else:
        print(f"Failed to fetch records: {response.status_code}")
        print(response.text)
else:
    print(f"Login failed: {response.status_code}")
    print(response.text)
