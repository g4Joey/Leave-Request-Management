"""
Create a few requests and walk them through stages to verify CEO visibility queues.
This script is idempotent for demo purposes.
"""
from django.contrib.auth import get_user_model
from django.utils import timezone
from leaves.models import LeaveType, LeaveRequest
from leaves.services import ApprovalWorkflowService

User = get_user_model()


def get_user(email: str):
    return User.objects.filter(email__iexact=email).first()


def create_request(employee_email: str, lt_name: str = 'Annual Leave') -> LeaveRequest:
    emp = get_user(employee_email)
    lt = LeaveType.objects.filter(name__iexact=lt_name).first()
    assert emp and lt, f"Missing user or leave type for {employee_email} / {lt_name}"
    # Avoid duplicates within same day window
    today = timezone.now().date()
    existing = LeaveRequest.objects.filter(employee=emp, start_date=today, end_date=today).first()
    if existing:
        return existing
    return LeaveRequest.objects.create(
        employee=emp,
        leave_type=lt,
        start_date=today,
        end_date=today,
        reason='Queue verification',
        status='pending',
    )


def approve_by(user_email: str, req: LeaveRequest):
    user = get_user(user_email)
    assert user, f"Approver {user_email} not found"
    handler = ApprovalWorkflowService.get_handler(req)
    if not handler.can_approve(user, req.status):
        return False
    # Drive status transitions using model helpers via services
    from leaves.views import LeaveRequestViewSet  # use same path as API
    # Simulate approve by calling service directly
    ApprovalWorkflowService.approve_request(req, user, 'ok')
    req.refresh_from_db()
    return True


def main():
    # Actors
    merban_staff = 'aakorfu@umbcapital.com'
    merban_mgr = 'jmankoe@umbcapital.com'
    merban_hr = 'hradmin@umbcapital.com'
    merban_ceo = 'ceo@umbcapital.com'

    sdsl_staff = 'asanunu@umbcapital.com'
    sdsl_ceo = 'sdslceo@umbcapital.com'

    sbl_staff = 'staff@sbl.com'
    sbl_ceo = 'sblceo@umbcapital.com'

    # 1) Merban flow: staff -> manager -> HR -> CEO
    mer_req = create_request(merban_staff)
    print(f"Merban created: id={mer_req.id} status={mer_req.status}")
    # manager approves
    approve_by(merban_mgr, mer_req)
    mer_req.refresh_from_db()
    print(f"Merban after manager: {mer_req.status}")
    # HR approves
    approve_by(merban_hr, mer_req)
    mer_req.refresh_from_db()
    print(f"Merban after HR: {mer_req.status}")

    # 2) SDSL flow: staff -> CEO -> HR(final)
    sdsl_req = create_request(sdsl_staff)
    print(f"SDSL created: id={sdsl_req.id} status={sdsl_req.status}")
    approve_by(sdsl_ceo, sdsl_req)
    sdsl_req.refresh_from_db()
    print(f"SDSL after CEO: {sdsl_req.status}")

    # 3) SBL flow: staff -> CEO -> HR(final)
    sbl_req = create_request(sbl_staff)
    print(f"SBL created: id={sbl_req.id} status={sbl_req.status}")
    approve_by(sbl_ceo, sbl_req)
    sbl_req.refresh_from_db()
    print(f"SBL after CEO: {sbl_req.status}")

    print('\nNow verify CEO queues via API endpoints:')
    print(' - /api/leaves/manager/pending_approvals/?stage=ceo')
    print(' - /api/leaves/manager/ceo_approvals_categorized/')


if __name__ == '__main__':
    main()
