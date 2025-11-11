#!/usr/bin/env python
"""Comprehensive analysis of affiliate display and CEO approval system."""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser as User, Affiliate, Department
from leaves.models import LeaveRequest
from users.serializers import UserSerializer, AffiliateSerializer
from django.db.models import Q
import json

def analyze_user_data():
    """Analyze all user data especially CEO users."""
    print("=== USER DATA ANALYSIS ===")
    
    # Get all CEO users
    ceos = User.objects.filter(role='ceo', is_active=True).order_by('affiliate__name')
    print(f"\nFound {ceos.count()} active CEO users:")
    
    for ceo in ceos:
        print(f"\n{ceo.email} (ID: {ceo.id})")
        print(f"  Full Name: '{ceo.get_full_name()}'")
        print(f"  First Name: '{ceo.first_name}'")
        print(f"  Last Name: '{ceo.last_name}'")
        print(f"  Role: {ceo.role}")
        print(f"  Affiliate: {ceo.affiliate}")
        print(f"  Affiliate ID: {ceo.affiliate_id}")
        print(f"  Department: {ceo.department}")
        print(f"  Department ID: {ceo.department_id}")
        print(f"  Is Active: {ceo.is_active}")
        
        # Test UserSerializer output for this CEO
        serializer = UserSerializer(ceo)
        data = serializer.data
        print(f"  UserSerializer Output:")
        print(f"    affiliate: '{data.get('affiliate', 'NOT_FOUND')}'")
        print(f"    affiliate_name: '{data.get('affiliate_name', 'NOT_FOUND')}'")
        print(f"    affiliate_id: {data.get('affiliate_id', 'NOT_FOUND')}")

def analyze_affiliate_serializer():
    """Test AffiliateSerializer for all affiliates."""
    print("\n=== AFFILIATE SERIALIZER ANALYSIS ===")
    
    affiliates = Affiliate.objects.all().order_by('name')
    
    for affiliate in affiliates:
        print(f"\n{affiliate.name} (ID: {affiliate.id})")
        
        # Test AffiliateSerializer
        serializer = AffiliateSerializer(affiliate)
        data = serializer.data
        print(f"  AffiliateSerializer Output:")
        print(f"    ceo: {data.get('ceo')}")
        
        # Manual CEO lookup for comparison
        ceo = User.objects.filter(
            role='ceo', 
            is_active=True
        ).filter(
            Q(affiliate=affiliate) | Q(department__affiliate=affiliate)
        ).first()
        
        print(f"  Manual CEO lookup: {ceo.get_full_name() if ceo else None}")

def analyze_staff_endpoint_structure():
    """Analyze the staff endpoint data structure."""
    print("\n=== STAFF ENDPOINT STRUCTURE ANALYSIS ===")
    
    from users.views import StaffManagementView
    
    # Simulate the staff endpoint for each affiliate
    affiliates = Affiliate.objects.all().order_by('name')
    
    for affiliate in affiliates:
        print(f"\n{affiliate.name} Staff Endpoint Simulation:")
        
        # Get departments for this affiliate
        departments = Department.objects.filter(affiliate=affiliate).prefetch_related('customuser_set')
        
        result = []
        
        # Add department-based staff
        for dept in departments:
            dept_staff = list(dept.customuser_set.filter(is_active=True))
            result.append({
                'name': dept.name,
                'staff': [
                    {
                        'id': user.id,
                        'name': user.get_full_name() or user.email,
                        'email': user.email,
                        'role': user.role,
                        'affiliate': user.affiliate.name if user.affiliate else None,
                        'department': dept.name
                    } for user in dept_staff
                ]
            })
        
        # Add individual employees (no department) for this affiliate
        individual_employees = User.objects.filter(
            affiliate=affiliate,
            department__isnull=True,
            is_active=True
        )
        
        if individual_employees.exists():
            result.append({
                'name': 'Individual Employees',
                'staff': [
                    {
                        'id': user.id,
                        'name': user.get_full_name() or user.email,
                        'email': user.email,
                        'role': user.role,
                        'affiliate': user.affiliate.name if user.affiliate else None,
                        'department': None
                    } for user in individual_employees
                ]
            })
        
        print(f"  Departments/Sections: {len(result)}")
        for section in result:
            print(f"    {section['name']}: {len(section['staff'])} staff")
            for staff in section['staff']:
                if staff['role'] == 'ceo':
                    print(f"      CEO: {staff['name']} - Affiliate: {staff['affiliate']}")

def analyze_leave_requests_and_approvals():
    """Analyze leave requests and approval flow for CEO users."""
    print("\n=== LEAVE REQUEST & APPROVAL ANALYSIS ===")
    
    # Get all leave requests
    requests = LeaveRequest.objects.all().select_related(
        'user', 'user__affiliate', 'user__department', 'user__department__affiliate'
    )
    
    print(f"Total Leave Requests: {requests.count()}")
    
    # Group by affiliate
    for affiliate in Affiliate.objects.all():
        affiliate_requests = requests.filter(
            Q(user__affiliate=affiliate) | Q(user__department__affiliate=affiliate)
        )
        
        print(f"\n{affiliate.name} Leave Requests: {affiliate_requests.count()}")
        
        # Find CEO for this affiliate
        ceo = User.objects.filter(
            role='ceo',
            is_active=True
        ).filter(
            Q(affiliate=affiliate) | Q(department__affiliate=affiliate)
        ).first()
        
        if ceo:
            print(f"  CEO: {ceo.get_full_name()} ({ceo.email})")
            
            # Check what requests this CEO should see
            # Based on approval logic, CEOs should see requests from their affiliate
            for req in affiliate_requests[:3]:  # Show first 3 requests
                print(f"    Request ID {req.id}: {req.user.get_full_name()} -> {req.leave_type} ({req.status})")

def main():
    """Run comprehensive analysis."""
    print("COMPREHENSIVE AFFILIATE & APPROVAL SYSTEM ANALYSIS")
    print("=" * 60)
    
    analyze_user_data()
    analyze_affiliate_serializer()
    analyze_staff_endpoint_structure()
    analyze_leave_requests_and_approvals()
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")

if __name__ == "__main__":
    main()