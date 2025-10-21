#!/usr/bin/env python
"""
CEO Setup and Manager Flow Test Script
"""

import os
import sys
import django

# Ensure project root is on sys.path when running as a script
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Department
from leaves.models import LeaveRequest, LeaveType
from datetime import datetime, timedelta

User = get_user_model()

def create_ceo_user():
    """Create CEO user for testing"""
    print("=== Creating CEO User ===")
    
    # Check if CEO already exists
    existing_ceo = User.objects.filter(role='ceo').first()
    if existing_ceo:
        print(f"✓ CEO user already exists: {existing_ceo.username} ({existing_ceo.email})")
        return existing_ceo
    
    # Create Executive department if needed
    executive_dept, created = Department.objects.get_or_create(
        name='Executive',
        defaults={'description': 'Executive leadership team'}
    )
    if created:
        print("✓ Created Executive department")
    
    # Create CEO user
    try:
        ceo_user = User.objects.create_user(
            username='ceo',
            email='ceo@company.com',
            password='CEOPassword123!',
            first_name='Chief',
            last_name='Executive Officer',
            employee_id='CEO001',
            role='ceo',
            department=executive_dept,
            is_staff=True,
            annual_leave_entitlement=30,
            is_active_employee=True
        )
        
        print("✓ CEO user created successfully!")
        print(f"   Username: {ceo_user.username}")
        print(f"   Email: {ceo_user.email}")
        print(f"   Password: CEOPassword123!")
        return ceo_user
        
    except Exception as e:
        print(f"❌ Error creating CEO user: {e}")
        return None

def test_manager_flow():
    """Test the manager leave request flow"""
    print("\n=== Testing Manager Leave Request Flow ===")

    hod = User.objects.filter(username='jmankoe').first()
    if not hod:
        print("❌ HOD jmankoe not found!")
        return
    
    # Get leave type
    leave_type = LeaveType.objects.filter(name='Annual Leave').first()
    if not leave_type:
        print("❌ Annual Leave type not found!")
        return
    
    # Create a test leave request for the manager
    start_date = datetime.now().date() + timedelta(days=14)  # 2 weeks from now
    end_date = start_date + timedelta(days=4)  # 5-day leave
    
    # Delete any existing test requests
    LeaveRequest.objects.filter(
        employee=hod,
        start_date__gte=datetime.now().date(),
        reason__icontains="Manager flow test"
    ).delete()
    
    # Create new request
    test_request = LeaveRequest.objects.create(
        employee=hod,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason="Manager flow test - should go directly to HR",
        status='manager_approved'  # Simulating what would happen in perform_create
    )
    
    print(f"✓ Created test request #{test_request.pk}")
    print(f"  Employee: {test_request.employee.username} (role: {test_request.employee.role})")
    print(f"  Status: {test_request.status} ← Should be 'manager_approved' (ready for HR)")
    print(f"  Dates: {test_request.start_date} to {test_request.end_date}")
    
    # Show the expected flow
    print(f"\n✓ Expected flow for manager's own request:")
    print(f"  1. Manager submits → Status: 'manager_approved' (bypasses self-approval)")
    print(f"  2. HR approves → Status: 'hr_approved'")  
    print(f"  3. CEO approves → Status: 'approved'")
    
    return test_request

def show_ceo_env_vars():
    """Show the environment variables needed for DigitalOcean"""
    print("\n=== DigitalOcean Environment Variables ===")
    print("Set these in your DigitalOcean App Platform environment variables:")
    print("")
    print("CEO_EMAIL=ceo@yourcompany.com")
    print("CEO_PASSWORD=YourSecurePassword123!")
    print("CEO_FIRST_NAME=Chief")
    print("CEO_LAST_NAME=Executive Officer")
    print("")
    print("The system will automatically create the CEO user on deployment.")

if __name__ == '__main__':
    create_ceo_user()
    test_manager_flow()
    show_ceo_env_vars()