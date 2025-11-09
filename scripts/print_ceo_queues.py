from django.contrib.auth import get_user_model
from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService

User = get_user_model()

CEOS = [
    'ceo@umbcapital.com',
    'sdslceo@umbcapital.com',
    'sblceo@umbcapital.com',
]


def get_user(email):
    return User.objects.filter(email__iexact=email).first()


def pending_for_ceo(ceo_email):
    u = get_user(ceo_email)
    if not u:
        return []
    candidates = LeaveRequest.objects.filter(status__in=['pending','hr_approved'])
    res = []
    for lr in candidates:
        handler = ApprovalWorkflowService.get_handler(lr)
        if handler.can_approve(u, lr.status):
            res.append({'id': lr.id, 'status': lr.status, 'employee': lr.employee.email})
    return res


def run():
    for email in CEOS:
        items = pending_for_ceo(email)
        print(f"\n{email} pending ({len(items)}):")
        for it in items:
            print(f"  - #{it['id']} {it['status']} by {it['employee']}")

if __name__ == '__main__':
    run()
