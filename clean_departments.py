#!/usr/bin/env python
"""
Remove all old departments and ensure only the new canonical departments exist.
This script will:
1. Delete all departments NOT in the canonical list 
2. Clean up duplicate departments in the canonical list
3. Migrate users from deleted departments to appropriate new ones
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.db import transaction
from users.models import Department, CustomUser, Affiliate
from django.contrib.auth import get_user_model

User = get_user_model()

# Canonical departments that should exist
CANONICAL_DEPARTMENTS = [
    'Finance & Accounts',
    'Government Securities', 
    'Pensions & Provident Fund',
    'Private Wealth & Mutual Fund',
    'HR & Admin',
    'Client Service/Marketing',
    'Corporate Finance',
    'IT',
    'Compliance',
    'Audit',
    'Executive',
]

# Migration mapping for old department names
DEPARTMENT_MIGRATION_MAP = {
    'Engineering': 'IT',
    'Human Resources': 'HR & Admin', 
    'Operations': 'IT',
    'IHL': 'Client Service/Marketing',
    'Accounts & Compliance': 'Finance & Accounts',
    'SDSL': 'Corporate Finance',  # This might be an affiliate, not department
    'Marketing': 'Client Service/Marketing',
    'Information Technology': 'IT',
    'Finance': 'Finance & Accounts',
    'Admin': 'HR & Admin',
    'Legal': 'Compliance',
    'Administration': 'HR & Admin',
}

def clean_departments():
    """Clean up department duplicates and old departments."""
    with transaction.atomic():
        print("🧹 Cleaning up departments...")
        
        # First, handle canonical departments (merge duplicates)
        for canonical_name in CANONICAL_DEPARTMENTS:
            departments = Department.objects.filter(name__iexact=canonical_name).order_by('id')
            if departments.count() > 1:
                # Keep the first one, merge others
                primary_dept = departments.first()
                print(f"✓ Found {departments.count()} duplicates of '{canonical_name}', keeping id={primary_dept.id}")
                
                for duplicate in departments[1:]:
                    # Move users from duplicate to primary
                    moved_count = User.objects.filter(department=duplicate).update(department=primary_dept)
                    print(f"  ↳ Moved {moved_count} users from duplicate {duplicate.id} to primary {primary_dept.id}")
                    duplicate.delete()
                    
        # Handle old departments that need migration
        migration_stats = {}
        for old_name, new_name in DEPARTMENT_MIGRATION_MAP.items():
            old_departments = Department.objects.filter(name__iexact=old_name)
            if old_departments.exists():
                # Find target canonical department
                target_dept = Department.objects.filter(name__iexact=new_name).first()
                if not target_dept:
                    # Create the canonical department if it doesn't exist
                    target_dept = Department.objects.create(
                        name=new_name,
                        description=f"Migrated from {old_name}"
                    )
                    print(f"✓ Created canonical department: {new_name}")
                
                total_migrated = 0
                for old_dept in old_departments:
                    migrated_count = User.objects.filter(department=old_dept).update(department=target_dept)
                    total_migrated += migrated_count
                    print(f"  ↳ Migrated {migrated_count} users from '{old_name}' (id={old_dept.id}) to '{new_name}'")
                    old_dept.delete()
                    
                if total_migrated > 0:
                    migration_stats[f"{old_name} → {new_name}"] = total_migrated
                    
        # Delete any remaining non-canonical departments
        all_departments = Department.objects.all()
        canonical_names_lower = [name.lower() for name in CANONICAL_DEPARTMENTS]
        
        for dept in all_departments:
            if dept.name.lower() not in canonical_names_lower:
                user_count = User.objects.filter(department=dept).count()
                if user_count > 0:
                    # Migrate to IT as default
                    default_dept = Department.objects.filter(name__iexact='IT').first()
                    if default_dept:
                        User.objects.filter(department=dept).update(department=default_dept)
                        print(f"⚠️  Migrated {user_count} users from unknown department '{dept.name}' to 'IT'")
                    else:
                        print(f"❌ ERROR: Could not migrate users from '{dept.name}' - no IT department found!")
                        continue
                
                print(f"🗑️  Deleting non-canonical department: '{dept.name}' (id={dept.id})")
                dept.delete()
                
        # Ensure all canonical departments exist
        created_count = 0
        for canonical_name in CANONICAL_DEPARTMENTS:
            dept, created = Department.objects.get_or_create(
                name=canonical_name,
                defaults={'description': f'Canonical {canonical_name} department'}
            )
            if created:
                created_count += 1
                print(f"✅ Created canonical department: {canonical_name}")
                
        print(f"\n📊 Department cleanup complete:")
        print(f"   • {len(CANONICAL_DEPARTMENTS)} canonical departments ensured")
        print(f"   • {created_count} new departments created")
        if migration_stats:
            print(f"   • User migrations:")
            for migration, count in migration_stats.items():
                print(f"     - {migration}: {count} users")
                
        # Final verification
        final_departments = Department.objects.all().order_by('name')
        print(f"\n🏢 Final department list ({final_departments.count()} departments):")
        for dept in final_departments:
            user_count = User.objects.filter(department=dept).count()
            affiliate_name = dept.affiliate.name if dept.affiliate else "No affiliate"
            print(f"   • {dept.name} (id={dept.id}, {user_count} users, {affiliate_name})")

if __name__ == '__main__':
    print("🚀 Starting department cleanup...")
    clean_departments()
    print("✅ Department cleanup completed!")