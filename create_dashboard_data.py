#!/usr/bin/env python
"""
Direct script to create leave balances and sample data for dashboard.
This will be run once in production to ensure dashboard displays data.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.utils import timezone
from leaves.models import LeaveBalance, LeaveType, LeaveRequest
from users.models import CustomUser

def create_dashboard_data():
    print("=== Creating Dashboard Data ===")
    
    current_year = timezone.now().year
    print(f"Working with year: {current_year}")
    
    # Get all active employees
    users = CustomUser.objects.filter(is_active=True, is_active_employee=True)
    print(f"Found {users.count()} active employees")
    
    # Get all active leave types
    leave_types = LeaveType.objects.filter(is_active=True)
    print(f"Found {leave_types.count()} leave types")
    
    # Default entitlements for common leave types
    default_entitlements = {
        'Annual Leave': 21,
        'Sick Leave': 10,
        'Casual Leave': 5,
        'Maternity Leave': 90,
        'Paternity Leave': 10,
        'Study Leave': 5
    }
    
    # Create leave balances for all users
    created_count = 0
    for user in users:
        for leave_type in leave_types:
            # Use default entitlement based on leave type name, fallback to 21
            entitled_days = default_entitlements.get(leave_type.name, 21)
            
            balance, created = LeaveBalance.objects.get_or_create(
                employee=user,
                leave_type=leave_type,
                year=current_year,
                defaults={
                    'entitled_days': entitled_days,
                    'used_days': 0,
                    'pending_days': 0,
                    'remaining_days': entitled_days
                }
            )
            if created:
                created_count += 1
                print(f"Created balance for {user.username} - {leave_type.name}: {entitled_days} days")
    
    print(f"Created {created_count} new leave balances")
    
    # Create a sample leave request if none exist
    recent_requests = LeaveRequest.objects.filter(
        created_at__year=current_year
    ).count()
    
    if recent_requests == 0 and users.exists():
        print("Creating sample leave request...")
        sample_user = users.first()
        sample_leave_type = leave_types[0] if leave_types else LeaveType.objects.first()
        
        if sample_leave_type and sample_user:
            LeaveRequest.objects.create(
                employee=sample_user,
                leave_type=sample_leave_type,
                start_date=timezone.now().date(),
                end_date=timezone.now().date() + timezone.timedelta(days=1),
                days_requested=2,
                reason="Sample leave request for testing",
                status='pending'
            )
            print("Created sample leave request")
    
    # Final verification
    total_balances = LeaveBalance.objects.filter(year=current_year).count()
    total_requests = LeaveRequest.objects.filter(created_at__year=current_year).count()
    
    print(f"\n=== FINAL STATUS ===")
    print(f"Total leave balances for {current_year}: {total_balances}")
    print(f"Total leave requests for {current_year}: {total_requests}")
    print("Dashboard data creation completed!")

if __name__ == "__main__":
    create_dashboard_data()