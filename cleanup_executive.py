#!/usr/bin/env python
"""
One-time script to clean up Executive departments and reassign users
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from users.models import Department, CustomUser
from django.db import transaction

def cleanup_executive_departments():
    print("Cleaning up Executive departments...")
    
    with transaction.atomic():
        # Find all Executive departments
        executive_depts = Department.objects.filter(name__iexact='Executive')
        
        if not executive_depts.exists():
            print("No Executive departments found.")
            return
        
        print(f"Found {executive_depts.count()} Executive department(s)")
        
        # Find a suitable default department for reassignment (IT or HR & Admin)
        default_dept = (
            Department.objects.filter(name='IT').first() or 
            Department.objects.filter(name='HR & Admin').first()
        )
        
        if not default_dept:
            print("ERROR: No suitable default department (IT or HR & Admin) found for reassignment")
            return
        
        # Make Executive users standalone (CEOs) instead of reassigning to departments
        total_moved = 0
        for exec_dept in executive_depts:
            users = CustomUser.objects.filter(department=exec_dept)
            user_count = users.count()
            
            if user_count > 0:
                # Show users being made standalone
                for user in users:
                    print(f"Making user standalone: {user.get_full_name()} ({user.email}) - removing from Executive department")
                
                # Make users standalone (department=None) - they become individual entities
                users.update(department=None)
                total_moved += user_count
                
            # Delete the Executive department
            exec_dept.delete()
            print(f"Deleted Executive department (id={exec_dept.pk})")
        
        print(f"Successfully made {total_moved} user(s) standalone and removed all Executive departments")

if __name__ == '__main__':
    cleanup_executive_departments()