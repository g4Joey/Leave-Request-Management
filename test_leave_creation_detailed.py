#!/usr/bin/env python3
"""
Detailed test for leave request creation to identify production issues
"""
import os
import sys
import django
from datetime import date, timedelta

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from leaves.models import LeaveType, LeaveBalance, LeaveRequest
from leaves.serializers import LeaveRequestSerializer
from django.utils import timezone

def test_leave_creation():
    print("=== Detailed Leave Request Creation Test ===")
    
    User = get_user_model()
    
    # Test for Augustine Akorfu
    try:
        user = User.objects.get(username='aakorfu')
        print(f"✅ Found user: {user.username} (ID: {user.id})")
    except User.DoesNotExist:
        print("❌ User aakorfu not found")
        return
    
    # Check leave types
    leave_types = LeaveType.objects.filter(is_active=True)
    print(f"✅ Active leave types: {leave_types.count()}")
    for lt in leave_types:
        print(f"  - {lt.name} (ID: {lt.id}) - Max days: {lt.max_days_per_request}")
    
    # Check balances
    current_year = timezone.now().year
    balances = LeaveBalance.objects.filter(employee=user, year=current_year)
    print(f"✅ Leave balances for {user.username} in {current_year}: {balances.count()}")
    for balance in balances:
        print(f"  - {balance.leave_type.name}: {balance.remaining_days} remaining (entitled: {balance.entitled_days}, used: {balance.used_days})")
    
    # Test creating a leave request using the serializer
    annual_leave = LeaveType.objects.filter(name__icontains='annual', is_active=True).first()
    if not annual_leave:
        print("❌ No Annual leave type found")
        return
    
    print(f"\n=== Testing Leave Request Creation ===")
    print(f"Using leave type: {annual_leave.name} (ID: {annual_leave.id})")
    
    # Test data similar to what would come from frontend
    start_date = date.today() + timedelta(days=10)
    end_date = start_date + timedelta(days=2)
    
    test_data = {
        'leave_type': annual_leave.id,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'reason': 'Test leave request from diagnostic script'
    }
    
    print(f"Test data: {test_data}")
    
    # Create serializer and validate
    serializer = LeaveRequestSerializer(data=test_data)
    
    print(f"\n=== Serializer Validation ===")
    if serializer.is_valid():
        print("✅ Serializer validation passed")
        print(f"Validated data: {serializer.validated_data}")
        
        # Try to save
        try:
            leave_request = serializer.save(employee=user)
            print(f"✅ Leave request created successfully!")
            print(f"  - ID: {leave_request.id}")
            print(f"  - Total days: {leave_request.total_days}")
            print(f"  - Working days: {leave_request.working_days}")
            print(f"  - Status: {leave_request.status}")
            
            # Check balance update
            balance = LeaveBalance.objects.get(
                employee=user,
                leave_type=annual_leave,
                year=current_year
            )
            print(f"  - Updated balance: {balance.remaining_days} remaining")
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving leave request: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print(f"❌ Serializer validation failed: {serializer.errors}")
        return False

def test_api_endpoint():
    """Test the API endpoint directly"""
    print(f"\n=== Testing API Endpoint ===")
    
    from django.test import RequestFactory
    from django.contrib.auth import get_user_model
    from leaves.views import LeaveRequestViewSet
    from rest_framework.test import force_authenticate
    
    User = get_user_model()
    user = User.objects.get(username='aakorfu')
    
    factory = RequestFactory()
    annual_leave = LeaveType.objects.filter(name__icontains='annual', is_active=True).first()
    
    start_date = date.today() + timedelta(days=15)
    end_date = start_date + timedelta(days=1)
    
    data = {
        'leave_type': annual_leave.id,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'reason': 'API endpoint test'
    }
    
    request = factory.post('/api/leaves/requests/', data, content_type='application/json')
    force_authenticate(request, user=user)
    
    view = LeaveRequestViewSet.as_view({'post': 'create'})
    
    try:
        response = view(request)
        print(f"✅ API Response status: {response.status_code}")
        if hasattr(response, 'data'):
            print(f"Response data: {response.data}")
        return response.status_code == 201
    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success1 = test_leave_creation()
    success2 = test_api_endpoint()
    
    print(f"\n=== Summary ===")
    print(f"Direct serializer test: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"API endpoint test: {'✅ PASSED' if success2 else '❌ FAILED'}")