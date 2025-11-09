from django.contrib.auth import get_user_model
from django.utils import timezone
from leaves.models import LeaveType, LeaveRequest

User = get_user_model()

def mk(email):
    u = User.objects.filter(email__iexact=email).first()
    if not u:
        # Auto-create missing SBL staff fallback if requested
        if email.lower() == 'staff@sbl.com':
            from users.models import Affiliate
            sbl = Affiliate.objects.filter(name__iexact='SBL').first()
            if not sbl:
                raise AssertionError('Affiliate SBL missing; cannot auto-create staff@sbl.com')
            u = User.objects.create_user(
                username='sbl_staff',
                email=email,
                password='ChangeMe123!',
                first_name='Eric',
                last_name='Nartey',
                role='senior_staff',
                affiliate=sbl,
                is_active_employee=True,
                is_demo=True,
            )
            print('Auto-created missing SBL staff user')
        else:
            raise AssertionError(f"User not found: {email}")
    lt = LeaveType.objects.filter(name__icontains='Annual').first()
    assert lt, 'Annual leave type not found'
    today = timezone.now().date()
    lr, created = LeaveRequest.objects.get_or_create(
        employee=u,
        leave_type=lt,
        start_date=today,
        end_date=today,
        defaults={
            'reason': 'Queue verification',
            'status': 'pending'
        }
    )
    print(email, '->', lr.id, lr.status, '(created)' if created else '(existing)')


def run():
    mk('aakorfu@umbcapital.com')
    mk('asanunu@umbcapital.com')
    mk('staff@sbl.com')
    print('done')

if __name__ == '__main__':
    run()
