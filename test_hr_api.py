#!/usr/bin/env python
"""Test HR approvals API endpoint"""
import requests

BASE_URL = "http://127.0.0.1:8000"

# Login as HR
print("Logging in as HR...")
login_resp = requests.post(f"{BASE_URL}/api/auth/token/", json={
    "username": "hradmin@umbcapital.com",
    "password": "1HRADMIN"
})

if login_resp.status_code != 200:
    print(f"❌ Login failed: {login_resp.status_code}")
    print(login_resp.text)
    exit(1)

token = login_resp.json()['access']
headers = {"Authorization": f"Bearer {token}"}
print("✓ Login successful\n")

# Get HR approvals categorized
print("Fetching HR approvals categorized...")
resp = requests.get(f"{BASE_URL}/api/leaves/manager/hr_approvals_categorized/", headers=headers)

if resp.status_code != 200:
    print(f"❌ Failed: {resp.status_code}")
    print(resp.text)
    exit(1)

data = resp.json()
print(f"✓ Response received\n")
print("=" * 80)
print("HR APPROVALS BY AFFILIATE")
print("=" * 80)

for affiliate, requests in data.get('groups', {}).items():
    print(f"\n{affiliate}: {len(requests)} requests")
    for req in requests:
        print(f"  LR#{req['id']}: {req['employee_name']} - Status: {req['status']}")

print(f"\nCounts: {data.get('counts')}")
print(f"Total: {data.get('total')}")
