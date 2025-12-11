import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser, Affiliate

print("Checking all affiliates and their users")
print("=" * 70)

affiliates = Affiliate.objects.all()
for aff in affiliates:
    print(f"\n{aff.name}:")
    users = CustomUser.objects.filter(affiliate=aff)
    print(f"  Users with this affiliate: {users.count()}")
    for user in users[:5]:
        print(f"    - {user.get_full_name()} ({user.email})")
        if user.department:
            print(f"      Dept: {user.department.name} (Aff: {user.department.affiliate.name if user.department.affiliate else 'None'})")
