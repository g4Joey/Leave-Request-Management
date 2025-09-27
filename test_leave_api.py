#!/usr/bin/env python3
"""
Quick test script to debug leave request submission issues
"""
import requests
import json
from datetime import datetime, timedelta

# Test configuration
BASE_URL = "http://127.0.0.1:8001"
USERNAME = "aakorfu"  # Augustine Akorfu
PASSWORD = "password123"  # Assuming this is the password

def test_leave_request():
    # Step 1: Login to get token
    print("=== Testing Leave Request Submission ===")
    print(f"1. Attempting login for user: {USERNAME}")
    
    login_response = requests.post(f"{BASE_URL}/api/auth/token/", json={
        "username": USERNAME,
        "password": PASSWORD
    })
    
    print(f"Login status: {login_response.status_code}")
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.text}")
        return
    
    token_data = login_response.json()
    access_token = token_data.get("access")
    print("Login successful!")
    
    # Step 2: Check leave balances
    print("\n2. Checking leave balances...")
    headers = {"Authorization": f"Bearer {access_token}"}
    
    balance_response = requests.get(f"{BASE_URL}/api/leaves/balances/", headers=headers)
    print(f"Balance check status: {balance_response.status_code}")
    
    if balance_response.status_code == 200:
        balances = balance_response.json()
        print("Leave balances:")
        for balance in balances:
            print(f"  - {balance['leave_type_name']}: {balance['remaining_days']} days remaining")
    else:
        print(f"Balance check failed: {balance_response.text}")
        return
    
    # Step 3: Get leave types
    print("\n3. Getting leave types...")
    types_response = requests.get(f"{BASE_URL}/api/leaves/types/", headers=headers)
    print(f"Leave types status: {types_response.status_code}")
    
    if types_response.status_code != 200:
        print(f"Leave types failed: {types_response.text}")
        return
    
    leave_types = types_response.json()
    if not leave_types:
        print("No leave types found!")
        return
    
    annual_leave = None
    for lt in leave_types:
        if "annual" in lt['name'].lower():
            annual_leave = lt
            break
    
    if not annual_leave:
        annual_leave = leave_types[0]  # Use first available
    
    print(f"Using leave type: {annual_leave['name']} (ID: {annual_leave['id']})")
    
    # Step 4: Submit leave request
    print("\n4. Submitting leave request...")
    
    # Get dates for next week (Monday to Friday)
    today = datetime.now().date()
    next_monday = today + timedelta(days=(7 - today.weekday()))
    next_friday = next_monday + timedelta(days=4)
    
    leave_request_data = {
        "leave_type": annual_leave['id'],
        "start_date": next_monday.strftime("%Y-%m-%d"),
        "end_date": next_friday.strftime("%Y-%m-%d"),
        "reason": "Test leave request for debugging"
    }
    
    print(f"Request data: {json.dumps(leave_request_data, indent=2)}")
    
    submit_response = requests.post(
        f"{BASE_URL}/api/leaves/requests/",
        json=leave_request_data,
        headers=headers
    )
    
    print(f"Submit status: {submit_response.status_code}")
    print(f"Response: {submit_response.text}")
    
    if submit_response.status_code == 201:
        print("✅ Leave request submitted successfully!")
    else:
        print("❌ Leave request submission failed!")
        try:
            error_data = submit_response.json()
            print("Error details:")
            for field, errors in error_data.items():
                if isinstance(errors, list):
                    for error in errors:
                        print(f"  - {field}: {error}")
                else:
                    print(f"  - {field}: {errors}")
        except:
            print(f"Raw error: {submit_response.text}")

if __name__ == "__main__":
    test_leave_request()