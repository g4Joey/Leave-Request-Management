#!/usr/bin/env python
"""
Debug affiliate-specific views and CEO display
"""
import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from rest_framework.test import APIClient
from users.models import CustomUser
from rest_framework_simplejwt.tokens import RefreshToken

def debug_affiliate_views():
    print("=== Affiliate Views Debug ===")
    
    # Get HR user for authentication
    hr_user = CustomUser.objects.filter(role='hr').first()
    client = APIClient()
    refresh = RefreshToken.for_user(hr_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    # Test each affiliate endpoint
    affiliates = [
        (1, "MERBAN CAPITAL"),
        (2, "SDSL"), 
        (3, "SBL")
    ]
    
    for aff_id, aff_name in affiliates:
        print(f"\n=== {aff_name} (ID: {aff_id}) ===")
        
        # 1. Test affiliate-specific staff endpoint
        print(f"1. Staff endpoint: /users/staff/?affiliate_id={aff_id}")
        response = client.get(f'/users/staff/?affiliate_id={aff_id}')
        
        if response.status_code == 200:
            if isinstance(response.data, list):
                print(f"   Found {len(response.data)} staff members/departments")
                for item in response.data:
                    if isinstance(item, dict):
                        # Check if this is a department with staff
                        if 'staff' in item:
                            dept_name = item.get('name', 'Unknown')
                            staff_list = item.get('staff', [])
                            print(f"   Department '{dept_name}': {len(staff_list)} staff")
                            for staff in staff_list:
                                if staff.get('role') == 'ceo':
                                    print(f"     CEO: {staff.get('name')} ({staff.get('email')})")
                        # Check if this is a direct staff member (SDSL/SBL format)
                        elif item.get('role') == 'ceo':
                            print(f"   CEO: {item.get('name')} ({item.get('email')})")
                            print(f"        Affiliate: {item.get('affiliate')}")
            else:
                print(f"   Response type: {type(response.data)}")
                print(f"   Response: {response.data}")
        else:
            print(f"   ERROR {response.status_code}: {response.data}")
        
        # 2. Test CEO-specific endpoint
        print(f"2. CEO endpoint: /users/staff/?affiliate_id={aff_id}&role=ceo")
        response = client.get(f'/users/staff/?affiliate_id={aff_id}&role=ceo')
        
        if response.status_code == 200:
            print(f"   CEO data: {response.data}")
        else:
            print(f"   ERROR {response.status_code}: {response.data}")
        
        # 3. Test affiliates endpoint (for CEO display in cards)
        print(f"3. Affiliates endpoint: /users/affiliates/")
        response = client.get('/users/affiliates/')
        
        if response.status_code == 200:
            for affiliate in response.data.get('results', response.data):
                if affiliate.get('id') == aff_id:
                    print(f"   Affiliate card data for {aff_name}:")
                    print(f"     CEO: {affiliate.get('ceo')}")
                    break
        print("-" * 50)

if __name__ == '__main__':
    debug_affiliate_views()