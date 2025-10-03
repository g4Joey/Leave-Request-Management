#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser

# Update Augustine to junior_staff
try:
    augustine = CustomUser.objects.get(first_name__icontains='augustine')
    augustine.role = 'junior_staff'
    augustine.save()
    print(f"✓ Updated {augustine.get_full_name()} to junior_staff")
except CustomUser.DoesNotExist:
    print("✗ Augustine not found")

# Update George Safo to senior_staff
try:
    george = CustomUser.objects.get(first_name__icontains='george', last_name__icontains='safo')
    george.role = 'senior_staff'
    george.save()
    print(f"✓ Updated {george.get_full_name()} to senior_staff")
except CustomUser.DoesNotExist:
    print("✗ George Safo not found")

print("Role updates complete!")