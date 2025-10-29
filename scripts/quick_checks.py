"""
Quick checks for affiliate/department visibility and leave submission rules.

Run with:
  python scripts/quick_checks.py
"""

import os
import sys
from datetime import date, timedelta


def setup_django():
    # Ensure project root is on sys.path
    here = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(here, '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
    import django
    django.setup()


def next_weekday(start: date, weekday: int) -> date:
    """Return the next date with given weekday (0=Mon..6=Sun) on or after start."""
    days_ahead = (weekday - start.weekday()) % 7
    return start + timedelta(days=days_ahead)


def main():
    setup_django()

    from users.models import Affiliate, Department
    from users.serializers import UserSerializer
    from leaves.models import LeaveType
    from leaves.serializers import LeaveRequestSerializer

    print("[check] Ensuring affiliates and MERBAN department exist...")
    merban, _ = Affiliate.objects.get_or_create(name='MERBAN CAPITAL', defaults={'description': 'Main entity'})
    sdsl, _ = Affiliate.objects.get_or_create(name='SDSL', defaults={'description': 'Standalone'})
    sbl, _ = Affiliate.objects.get_or_create(name='SBL', defaults={'description': 'Standalone'})

    merban_dept, _ = Department.objects.get_or_create(
        name='HR & Admin',
        affiliate=merban,
        defaults={'description': 'Human Resources'}
    )

    print("[info] Affiliates:", list(Affiliate.objects.values_list('name', flat=True)))
    print("[info] MERBAN departments:", list(Department.objects.filter(affiliate=merban).values_list('name', flat=True)))

    # Create or reuse test users
    print("[check] Creating test users (MERBAN with department, SDSL without department)...")
    def ensure_user(email: str, first: str, last: str, role: str, affiliate_id=None, department_id=None):
        from users.models import CustomUser
        u = CustomUser.objects.filter(email=email).first()
        if u:
            return u
        payload = {
            'email': email,
            'first_name': first,
            'last_name': last,
            'role': role,
            'affiliate_id': affiliate_id,
            'department_id': department_id,
            'password': 'Passw0rd!'
        }
        ser = UserSerializer(data=payload)
        ser.is_valid(raise_exception=True)
        return ser.save()

    merban_user = ensure_user(
        email='merban.test.user@example.com',
        first='Merban', last='Tester', role='junior_staff',
        affiliate_id=merban.id, department_id=merban_dept.id
    )
    sdsl_user = ensure_user(
        email='sdsl.test.user@example.com',
        first='SDSL', last='Tester', role='junior_staff',
        affiliate_id=sdsl.id, department_id=None
    )

    print(f"[ok] MERBAN user: {merban_user.get_full_name()} | affiliate={merban_user.affiliate.name if merban_user.affiliate else None} | dept={merban_user.department.name if merban_user.department else None}")
    print(f"[ok] SDSL user: {sdsl_user.get_full_name()} | affiliate={sdsl_user.affiliate.name if sdsl_user.affiliate else None} | dept={sdsl_user.department.name if sdsl_user.department else None}")

    # Ensure a leave type exists
    lt, _ = LeaveType.objects.get_or_create(name='Annual Leave', defaults={'description': 'Annual'})

    # Build a next-year leave request (3 working days starting from first Monday of next year)
    today = date.today()
    first_of_next_year = date(today.year + 1, 1, 1)
    start = next_weekday(first_of_next_year, 0)  # Monday
    end = start + timedelta(days=4)  # up to Friday (covers 5 calendar days, 5 weekdays; serializer counts)

    # Serialize a leave request for the MERBAN user
    print("[check] Submitting next-year leave request via serializer...")
    class _Req:
        def __init__(self, user):
            self.user = user

    ctx = {'request': _Req(merban_user)}
    lr_payload = {
        'leave_type': lt.id,
        'start_date': start,
        'end_date': end,
        'reason': 'Quick check request'
    }
    lr_ser = LeaveRequestSerializer(data=lr_payload, context=ctx)
    if lr_ser.is_valid():
        instance = lr_ser.save()
        print(f"[ok] Leave request created: id={instance.id}, range={instance.range_with_days}")
    else:
        print("[warn] Leave request errors:", lr_ser.errors)

    # Probe demo-visibility policy
    from django.test import RequestFactory
    from leave_management.views import demo_visibility
    rf = RequestFactory()
    resp = demo_visibility(rf.get('/api/probe/demo-visibility'))
    try:
        import json
        info = json.loads(resp.content.decode())
        print("[ok] Demo-visibility probe:", info)
    except Exception as e:
        print("[warn] Could not parse demo-visibility response:", e)

    print("[done] Quick checks completed.")


if __name__ == '__main__':
    sys.exit(main())
