import os
import sys
from pathlib import Path
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import django
django.setup()

from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.test import APIRequestFactory, force_authenticate

from users.models import Affiliate
from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService, ApprovalRoutingService
from leaves.views import ManagerLeaveViewSet


STATUSES = ['pending', 'manager_approved', 'hr_approved', 'ceo_approved', 'approved', 'rejected']


def reason_cannot(leave, ceo_user):
    try:
        handler = ApprovalWorkflowService.get_handler(leave)
        flow = handler.get_approval_flow()
        required = flow.get(leave.status)
        # Affiliate name for employee
        emp_aff = ''
        if getattr(leave.employee, 'affiliate', None):
            emp_aff = (leave.employee.affiliate.name or '').strip().upper()
        elif getattr(leave.employee, 'department', None) and getattr(leave.employee.department, 'affiliate', None):
            emp_aff = (leave.employee.department.affiliate.name or '').strip().upper()
        ceo_aff = (getattr(getattr(ceo_user, 'affiliate', None), 'name', '') or '').strip().upper()
        expected_ceo = ApprovalRoutingService.get_ceo_for_employee(leave.employee)
        if required != 'ceo':
            return f"not at CEO stage (status={leave.status}, requires={required})"
        if not expected_ceo:
            return f"no CEO resolved for employee affiliate='{emp_aff}'"
        if getattr(expected_ceo, 'id', None) != getattr(ceo_user, 'id', None):
            return f"affiliate CEO mismatch (emp_aff='{emp_aff}' expected_ceo_id={expected_ceo.id} != this_ceo_id={ceo_user.id} this_ceo_aff='{ceo_aff}')"
        return "unknown"
    except Exception as e:
        return f"error: {e}"


def check_ceo(ceo):
    print(f"\n=== CEO {ceo.id} {ceo.email} aff='{getattr(getattr(ceo,'affiliate',None),'name',None)}' ===")
    # Candidate requests (wide net)
    qs = LeaveRequest.objects.filter(status__in=STATUSES).select_related('employee__affiliate', 'employee__department__affiliate').order_by('-created_at')

    can_ids = []
    cannot = []
    for lr in qs:
        can = False
        try:
            can = ApprovalWorkflowService.can_user_approve(lr, ceo)
        except Exception:
            can = False
        if can:
            can_ids.append(lr.id)
        else:
            cannot.append((lr.id, reason_cannot(lr, ceo)))

    print(f"can_approve count={len(can_ids)} ids={can_ids[:25]}")
    print("cannot approve (first 25):")
    for i, (lid, why) in enumerate(cannot[:25], 1):
        print(f"  {i:02d}) lr#{lid}: {why}")

    # Compare with endpoint output for this CEO
    factory = APIRequestFactory()
    req = factory.get('/api/leaves/manager/pending_approvals/')
    force_authenticate(req, user=ceo)
    view = ManagerLeaveViewSet.as_view({'get': 'pending_approvals'})
    resp = view(req)
    data = getattr(resp, 'data', {}) or {}
    ids_endpoint = [r.get('id') for r in data.get('requests', [])]
    print(f"endpoint pending_approvals count={len(ids_endpoint)} ids={ids_endpoint[:25]}")


def main():
    User = get_user_model()
    ceos = list(User.objects.filter(role='ceo', is_active=True))
    if not ceos:
        print('No CEO users found.')
        return
    for c in ceos:
        check_ceo(c)


if __name__ == '__main__':
    main()
