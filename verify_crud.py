
import os
import django
from django.test import Client
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from leaves.models import LeaveRequest, LeaveType
User = get_user_model()

def run_verification():
    print("🚀 Starting Backend CRUD Verification...\n")
    client = Client()

    # 1. Verify Users Exist
    hr = User.objects.get(email='hradmin@umbcapital.com')
    staff = User.objects.get(email='gsafo@umbcapital.com')
    manager = User.objects.get(email='jmankoe@umbcapital.com')
    print(f"✅ Users Verified: HR({hr.pk}), Staff({staff.pk}), Manager({manager.pk})")

    # 2. Login as Staff
    login_successful = client.login(username='gsafo@umbcapital.com', password='Georgesafo')
    if login_successful:
        print("✅ Login (Staff): Successful")
    else:
        print("❌ Login (Staff): Failed")
        return

    # 3. Create Leave Request (Create)
    # Ensure LeaveType exists
    lt, _ = LeaveType.objects.get_or_create(
        name="Annual Leave", 
        defaults={'max_days_per_request': 20, 'requires_medical_certificate': False}
    )
    
    leave_data = {
        'leave_type': lt.id,
        'start_date': '2026-06-02',
        'end_date': '2026-06-06',
        'reason': 'Vacation test'
    }
    
    # We need to get a token or use session auth. Client.login uses session.
    # The API might be JWT only. Let's try posting to the API endpoint with session auth first.
    # If API uses strictly JWT, we might need to fetch token first.
    # Let's assume standard viewsets permissions allow IsAuthenticated which session provides in tests.
    
    response = client.post('/api/leaves/requests/', data=leave_data, content_type='application/json')
    
    if response.status_code == 201:
        print(f"✅ CREATE Leave Request: Success (ID: {response.data['id']})")
        leave_id = response.data['id']
    elif response.status_code == 401:
        print("⚠️  API requires JWT. Switching to JWT simulation.")
        # Get Token
        resp = client.post('/api/auth/token/', {'username': 'gsafo@umbcapital.com', 'password': 'Georgesafo'}, content_type='application/json')
        token = resp.data['access']
        header = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        
        # Retry Create
        response = client.post('/api/leaves/requests/', data=leave_data, content_type='application/json', **header)
        if response.status_code == 201:
             print(f"✅ CREATE Leave Request (JWT): Success (ID: {response.data['id']})")
             leave_id = response.data['id']
        else:
             print(f"❌ CREATE Leave Request Failed: {response.status_code} {response.content}")
             return
    else:
        print(f"❌ CREATE Leave Request Failed: {response.status_code} {response.content}")
        # Try finding why
        return

    # 4. Read Leave Requests (Read)
    if 'header' in locals():
         response = client.get('/api/leaves/requests/', **header)
    else:
         response = client.get('/api/leaves/requests/')
         
    if response.status_code == 200:
        count = len(response.data['results'])
        print(f"✅ READ Leave Requests: Success (Found {count} requests)")
    else:
        print(f"❌ READ Leave Requests Failed: {response.status_code}")

    # 5. Approve as Manager (Update)
    print("\n--- Switching to Manager ---")
    
    # Login Manager to get token
    resp = client.post('/api/auth/token/', {'username': 'jmankoe@umbcapital.com', 'password': 'Atokwamena'}, content_type='application/json')
    manager_token = resp.data['access']
    manager_header = {'HTTP_AUTHORIZATION': f'Bearer {manager_token}'}
    
    # Approve
    approve_data = {'status': 'approved', 'comments': 'Approved by script'}
    # Note: Endpoint details depend on implementation. Usually PATCH /api/leaves/requests/{id}/ or specific action.
    # Standard ModelViewSet update
    response = client.patch(f'/api/leaves/requests/{leave_id}/', data=approve_data, content_type='application/json', **manager_header)
    
    if response.status_code in [200, 204]:
        print(f"✅ UPDATE Request (Approve): Success")
        updated_req = LeaveRequest.objects.get(pk=leave_id)
        print(f"   Current Status in DB: {updated_req.status}")
    else:
        # Try custom action endpoint if standard update failed (e.g. /approve/)
        response = client.post(f'/api/leaves/requests/{leave_id}/approve/', data={}, content_type='application/json', **manager_header)
        if response.status_code == 200:
             print(f"✅ UPDATE Request (Action Approve): Success")
             updated_req = LeaveRequest.objects.get(pk=leave_id)
             print(f"   Current Status in DB: {updated_req.status}")
        else:
             print(f"❌ UPDATE Request Failed: {response.status_code} {response.content}")

    # 6. Check Dashboard Stats (Missing Endpoint Check)
    print("\n--- Checking Dashboard Stats ---")
    response = client.get('/api/dashboard/stats/', **manager_header)
    if response.status_code == 200:
        print("✅ Dashboard Stats: Endpoint Works")
    elif response.status_code == 404:
        print("❌ Dashboard Stats: Endpoint NOT FOUND (As expected from URL audit)")
    else:
        print(f"⚠️  Dashboard Stats: Unexpected status {response.status_code}")

if __name__ == '__main__':
    try:
        run_verification()
    except Exception as e:
        print(f"❌ Verification Logic Error: {e}")
