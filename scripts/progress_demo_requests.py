"""Advance demo requests through their workflow to set up CEO queues.
Merban: staff -> manager -> HR (expect CEO queue hr_approved)
SDSL/SBL: staff -> CEO (expect ceo_approved or approved depending on flow)
"""
from django.contrib.auth import get_user_model
from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService

User = get_user_model()

ACTORS = {
    'merban_staff': 'aakorfu@umbcapital.com',
    'merban_manager': 'jmankoe@umbcapital.com',
    'merban_hr': 'hradmin@umbcapital.com',
    'merban_ceo': 'ceo@umbcapital.com',
    'sdsl_staff': 'asanunu@umbcapital.com',
    'sdsl_ceo': 'sdslceo@umbcapital.com',
    'sbl_staff': 'staff@sbl.com',
    'sbl_ceo': 'sblceo@umbcapital.com',
}


def get_user(email):
    return User.objects.filter(email__iexact=email).first()


def approve(email, lr: LeaveRequest):
    u = get_user(email)
    if not u:
        print(f"Approver missing: {email}")
        return False
    handler = ApprovalWorkflowService.get_handler(lr)
    if handler.can_approve(u, lr.status):
        ApprovalWorkflowService.approve_request(lr, u, 'ok')
        lr.refresh_from_db()
        print(f"Approved by {email} -> status {lr.status}")
        return True
    else:
        print(f"Cannot approve at this stage: {email} for status {lr.status}")
        return False


def run():
    # Merban flow
    mer = LeaveRequest.objects.filter(employee__email__iexact=ACTORS['merban_staff']).order_by('-id').first()
    if mer:
        approve(ACTORS['merban_manager'], mer)  # pending -> manager_approved
        approve(ACTORS['merban_hr'], mer)       # manager_approved -> hr_approved
        # Do NOT CEO approve yet; we want it visible in CEO queue
    else:
        print('Merban request missing')

    # SDSL flow: pending -> ceo_approved -> approved (HR final) but we stop after CEO approve to show queue before HR final
    sdsl = LeaveRequest.objects.filter(employee__email__iexact=ACTORS['sdsl_staff']).order_by('-id').first()
    if sdsl:
        approve(ACTORS['sdsl_ceo'], sdsl)  # pending -> ceo_approved
    else:
        print('SDSL request missing')

    # SBL flow
    sbl = LeaveRequest.objects.filter(employee__email__iexact=ACTORS['sbl_staff']).order_by('-id').first()
    if sbl:
        approve(ACTORS['sbl_ceo'], sbl)  # pending -> ceo_approved
    else:
        print('SBL request missing')

    print('\nStatuses:')
    for label, email in [('Merban', ACTORS['merban_staff']), ('SDSL', ACTORS['sdsl_staff']), ('SBL', ACTORS['sbl_staff'])]:
        lr = LeaveRequest.objects.filter(employee__email__iexact=email).order_by('-id').first()
        if lr:
            print(f"{label}: id={lr.id} status={lr.status}")

if __name__ == '__main__':
    run()
