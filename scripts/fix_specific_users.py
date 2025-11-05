import os
import sys
from pathlib import Path
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import django
django.setup()

from django.db import transaction
from django.contrib.auth import get_user_model
from users.models import Affiliate, Department


def ensure_merban_hr_department():
    aff = Affiliate.objects.filter(name__iexact='MERBAN CAPITAL').first()
    if not aff:
        aff = Affiliate.objects.create(name='MERBAN CAPITAL')
    dept = Department.objects.filter(name__iexact='HR & Admin', affiliate=aff).first()
    if not dept:
        dept = Department.objects.create(name='HR & Admin', affiliate=aff, description='Human Resources and Administration')
    return aff, dept


def main():
    User = get_user_model()
    with transaction.atomic():
        # Fix HR user 17
        hr = User.objects.filter(pk=17).first() or User.objects.filter(email__iexact='hr@umbcapital.com').first()
        if hr:
            merban, hr_dept = ensure_merban_hr_department()
            hr.affiliate = merban
            hr.department = hr_dept
            if hr.role != 'hr':
                hr.role = 'hr'
            hr.save(update_fields=['affiliate', 'department', 'role'])
            print(f"Updated HR user {hr.id} -> affiliate={merban.name}, department={hr_dept.name}")
        else:
            print("HR user not found (id 17 or email hr@umbcapital.com)")

        # Adjust admin superuser 4
        admin = User.objects.filter(pk=4).first() or User.objects.filter(email__iexact='admin@company.com').first()
        if admin:
            admin.is_superuser = True
            admin.is_staff = True
            # Allow no affiliate for superuser by our model.clean short-circuit
            admin.affiliate = None
            admin.save(update_fields=['is_superuser', 'is_staff', 'affiliate'])
            print(f"Updated Admin user {admin.id} -> superuser=True, affiliate=None")
        else:
            print("Admin user not found (id 4 or email admin@company.com)")

if __name__ == '__main__':
    main()
