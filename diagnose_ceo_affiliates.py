#!/usr/bin/env python
"""
Diagnostic script to check CEO and employee affiliate assignments.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser, Affiliate, Department
from leaves.models import LeaveRequest
from leaves.services import ApprovalRoutingService

def main():
    print("=" * 80)
    print("CEO AND EMPLOYEE AFFILIATE DIAGNOSTIC")
    print("=" * 80)
    
    # 1. List all affiliates
    print("\n1. AFFILIATES IN DATABASE:")
    print("-" * 80)
    affiliates = Affiliate.objects.all()
    for aff in affiliates:
        print(f"  - {aff.name} (ID: {aff.id})")
    
    # 2. List all CEOs and their affiliates
    print("\n2. CEOS AND THEIR AFFILIATES:")
    print("-" * 80)
    ceos = CustomUser.objects.filter(role='ceo', is_active=True)
    for ceo in ceos:
        aff_name = getattr(ceo.affiliate, 'name', 'NO AFFILIATE') if ceo.affiliate else 'NO AFFILIATE'
        print(f"  - {ceo.email} ({ceo.get_full_name()})")
        print(f"    Affiliate: {aff_name}")
        print(f"    Affiliate ID: {ceo.affiliate_id}")
    
    # 3. Check specific users mentioned in the issue
    print("\n3. SPECIFIC USERS:")
    print("-" * 80)
    test_users = [
        'ceo@umbcapital.com',
        'sdslceo@umbcapital.com',
        'sblceo@umbcapital.com',
        'augustine@umbcapital.com',
        'jmankoe@umbcapital.com'
    ]
    
    for email in test_users:
        try:
            user = CustomUser.objects.get(email=email)
            print(f"\n  {user.email} ({user.get_full_name()}):")
            print(f"    Role: {user.role}")
            print(f"    User Affiliate: {getattr(user.affiliate, 'name', 'None') if user.affiliate else 'None'}")
            print(f"    User Affiliate ID: {user.affiliate_id}")
            
            if user.department:
                print(f"    Department: {user.department.name}")
                dept_aff = getattr(user.department.affiliate, 'name', 'None') if user.department.affiliate else 'None'
                print(f"    Department Affiliate: {dept_aff}")
            else:
                print(f"    Department: None")
            
            # Get expected CEO for this user
            expected_ceo = ApprovalRoutingService.get_ceo_for_employee(user)
            if expected_ceo:
                print(f"    Expected CEO: {expected_ceo.email} ({expected_ceo.get_full_name()})")
            else:
                print(f"    Expected CEO: None found!")
                
        except CustomUser.DoesNotExist:
            print(f"\n  {email}: NOT FOUND")
    
    # 4. Check pending leave requests
    print("\n4. PENDING LEAVE REQUESTS REQUIRING CEO APPROVAL:")
    print("-" * 80)
    pending_lr = LeaveRequest.objects.filter(status__in=['hr_approved', 'pending']).select_related(
        'employee', 'employee__affiliate', 'employee__department', 'employee__department__affiliate'
    )
    
    for lr in pending_lr:
        emp = lr.employee
        print(f"\n  LR#{lr.id} - {emp.get_full_name()} ({emp.email})")
        print(f"    Status: {lr.status}")
        print(f"    Employee Role: {emp.role}")
        print(f"    Employee Affiliate: {getattr(emp.affiliate, 'name', 'None') if emp.affiliate else 'None'}")
        
        if emp.department:
            print(f"    Employee Department: {emp.department.name}")
            dept_aff = getattr(emp.department.affiliate, 'name', 'None') if emp.department.affiliate else 'None'
            print(f"    Department Affiliate: {dept_aff}")
        
        # Get affiliate name using routing service
        aff_name = ApprovalRoutingService.get_employee_affiliate_name(emp)
        print(f"    Routing Service Affiliate: {aff_name}")
        
        # Get expected CEO
        expected_ceo = ApprovalRoutingService.get_ceo_for_employee(emp)
        if expected_ceo:
            print(f"    Expected CEO: {expected_ceo.email}")
            print(f"    CEO Affiliate: {getattr(expected_ceo.affiliate, 'name', 'None') if expected_ceo.affiliate else 'None'}")
        else:
            print(f"    Expected CEO: NONE FOUND!")
    
    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()
