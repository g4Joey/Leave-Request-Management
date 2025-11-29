#!/usr/bin/env python
"""Test real HTTP approval flow"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

print("=" * 80)
print("TESTING REAL HTTP CEO APPROVAL FLOW")
print("=" * 80)

# Login
print("\n1. Logging in as Merban CEO...")
login_resp = requests.post(f"{BASE_URL}/api/auth/token/", json={
    "username": "ceo@umbcapital.com",
    "password": "MerbanCEO"
})

if login_resp.status_code != 200:
    print(f"❌ Login failed: {login_resp.status_code}")
    print(login_resp.text)
    exit(1)

token = login_resp.json()['access']
headers = {"Authorization": f"Bearer {token}"}
print("✓ Login successful")

# Get CEO approvals
print("\n2. Fetching CEO approvals...")
cat_resp = requests.get(f"{BASE_URL}/api/leaves/manager/ceo_approvals_categorized/", headers=headers)

if cat_resp.status_code != 200:
    print(f"❌ Failed to get approvals: {cat_resp.status_code}")
    print(cat_resp.text)
    exit(1)

data = cat_resp.json()
print(f"✓ Got approvals - Total: {data.get('total_count')}")
print(f"  Counts: {data.get('counts')}")

# Find a request to approve
test_request = None
for cat_name, category_requests in data.get('categories', {}).items():
    if category_requests:
        test_request = category_requests[0]
        print(f"\n3. Testing with first request from {cat_name.upper()} category:")
        print(f"  LR#{test_request['id']} - {test_request['employee_name']}")
        print(f"  Role: {test_request.get('employee_role')}")
        print(f"  Department: {test_request.get('employee_department')}")
        print(f"  Affiliate: {test_request.get('employee_department_affiliate')}")
        print(f"  Status: {test_request['status']}")
        break

if not test_request:
    print("\n❌ No requests found to test")
    exit(1)

# Try to approve
import requests as req_lib
print(f"\n4. Attempting to approve LR#{test_request['id']}...")
approve_resp = req_lib.put(  # PUT not POST
    f"{BASE_URL}/api/leaves/manager/{test_request['id']}/approve/",
    headers=headers,
    json={"comments": "Test approval via real HTTP"}
)

print(f"\nApproval Response:")
print(f"  Status: {approve_resp.status_code}")

if approve_resp.status_code == 200:
    print(f"  ✓ SUCCESS!")
    result = approve_resp.json()
    print(f"  Message: {result.get('message')}")
    print(f"  New status: {result.get('status')}")
else:
    print(f"  ❌ FAILED")
    try:
        error = approve_resp.json()
        print(f"  Error: {json.dumps(error, indent=2)}")
    except:
        print(f"  Raw response: {approve_resp.text}")
