#!/usr/bin/env python
import os
import sys
import django

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from leaves.models import LeaveRequest
from django.db.models import Q

def debug_ceo_filtering():
    print("🔍 Debug CEO Filtering Logic")
    print("=" * 50)
    
    # Get Benjamin (CEO)
    benjamin = CustomUser.objects.get(email='ceo@umbcapital.com')
    print(f"✅ CEO: {benjamin.username}")
    print(f"   Affiliate: {benjamin.affiliate}")
    print(f"   Affiliate type: {type(benjamin.affiliate)}")
    
    print()
    
    # Get the hr_approved request
    hr_req = LeaveRequest.objects.get(id=20)
    employee = hr_req.employee
    print(f"📋 HR Approved Request: ID {hr_req.id}")
    print(f"   Employee: {employee.username} ({employee.email})")
    print(f"   Employee affiliate: {employee.affiliate}")
    print(f"   Employee affiliate type: {type(employee.affiliate)}")
    print(f"   Employee department: {getattr(employee, 'department', 'Not set')}")
    
    # Check if employee has department
    if hasattr(employee, 'department') and employee.department:
        dept = employee.department
        print(f"   Department affiliate: {getattr(dept, 'affiliate', 'Not set')}")
    else:
        print(f"   Department affiliate: None (no department)")
    
    print()
    
    # Test the exact filtering logic
    print("🔍 Testing CEO filtering conditions:")
    
    # Condition 1: employee__affiliate=ceo_affiliate
    cond1 = LeaveRequest.objects.filter(employee__affiliate=benjamin.affiliate)
    print(f"   employee__affiliate={benjamin.affiliate}: {cond1.count()} requests")
    if cond1.exists():
        for req in cond1:
            print(f"     • ID {req.id}: {req.employee.username} (status: {req.status})")
    
    # Condition 2: employee__department__affiliate=ceo_affiliate
    cond2 = LeaveRequest.objects.filter(employee__department__affiliate=benjamin.affiliate)
    print(f"   employee__department__affiliate={benjamin.affiliate}: {cond2.count()} requests")
    if cond2.exists():
        for req in cond2:
            print(f"     • ID {req.id}: {req.employee.username} (status: {req.status})")
    
    # Combined condition with OR
    combined = LeaveRequest.objects.filter(
        Q(employee__affiliate=benjamin.affiliate) | Q(employee__department__affiliate=benjamin.affiliate)
    )
    print(f"   Combined OR condition: {combined.count()} requests")
    if combined.exists():
        for req in combined:
            print(f"     • ID {req.id}: {req.employee.username} (status: {req.status})")
    
    # Full CEO filter
    full_filter = LeaveRequest.objects.filter(
        Q(employee__affiliate=benjamin.affiliate) | Q(employee__department__affiliate=benjamin.affiliate)
    ).filter(status__in=['pending', 'hr_approved', 'ceo_approved', 'approved', 'rejected'])
    print(f"   Full CEO filter: {full_filter.count()} requests")
    if full_filter.exists():
        for req in full_filter:
            print(f"     • ID {req.id}: {req.employee.username} (status: {req.status})")
    
    print()
    
    # Test affiliate comparison directly
    print("🔍 Testing affiliate comparison:")
    print(f"   employee.affiliate == benjamin.affiliate: {employee.affiliate == benjamin.affiliate}")
    print(f"   str(employee.affiliate) == str(benjamin.affiliate): {str(employee.affiliate) == str(benjamin.affiliate)}")
    print(f"   employee.affiliate.id == benjamin.affiliate.id: {employee.affiliate.id == benjamin.affiliate.id}")

if __name__ == "__main__":
    debug_ceo_filtering()