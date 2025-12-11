"""
Sync local departments to match production canonical departments
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import Department, Affiliate

# Canonical departments that should exist in production
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
]

print("=" * 80)
print("SYNCING DEPARTMENTS TO MATCH PRODUCTION")
print("=" * 80)

# Get Merban Capital affiliate
merban = Affiliate.objects.filter(name__icontains='merban').first()
if not merban:
    print("❌ ERROR: Merban Capital affiliate not found!")
    exit(1)

print(f"\nMerban Capital affiliate: {merban.name} (id={merban.pk})")

# Get existing departments
existing_depts = Department.objects.filter(affiliate=merban)
print(f"\nExisting Merban departments: {existing_depts.count()}")
for dept in existing_depts:
    print(f"  - {dept.name}")

# Create canonical departments
print(f"\n{'='*80}")
print("CREATING/UPDATING CANONICAL DEPARTMENTS")
print('='*80)

created_count = 0
existing_count = 0

for dept_name in CANONICAL_DEPARTMENTS:
    dept, created = Department.objects.get_or_create(
        name=dept_name,
        affiliate=merban,
        defaults={
            'description': f'{dept_name} department'
        }
    )
    
    if created:
        print(f"✓ Created: {dept_name}")
        created_count += 1
    else:
        print(f"  Already exists: {dept_name}")
        existing_count += 1

print(f"\n{'='*80}")
print("SUMMARY")
print('='*80)
print(f"✓ Created: {created_count}")
print(f"  Already existed: {existing_count}")
print(f"  Total canonical: {len(CANONICAL_DEPARTMENTS)}")

# Show all Merban departments after sync
print(f"\n{'='*80}")
print("ALL MERBAN DEPARTMENTS AFTER SYNC")
print('='*80)

all_merban_depts = Department.objects.filter(affiliate=merban).order_by('name')
print(f"\nTotal: {all_merban_depts.count()}")
for dept in all_merban_depts:
    users_count = dept.customuser_set.count()
    canonical = "✓" if dept.name in CANONICAL_DEPARTMENTS else "⚠"
    print(f"  {canonical} {dept.name} ({users_count} users)")

# Show non-canonical departments
non_canonical = all_merban_depts.exclude(name__in=CANONICAL_DEPARTMENTS)
if non_canonical.exists():
    print(f"\n{'='*80}")
    print("NON-CANONICAL DEPARTMENTS (Consider removing)")
    print('='*80)
    for dept in non_canonical:
        users = dept.customuser_set.all()
        print(f"\n  ⚠ {dept.name} (id={dept.pk})")
        if users.exists():
            print(f"    Has {users.count()} users:")
            for u in users:
                print(f"      - {u.get_full_name()} ({u.role})")
        else:
            print(f"    No users - safe to delete")
