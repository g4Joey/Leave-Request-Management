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
from leaves.models import LeaveRequest
from leaves.services import ApprovalRoutingService, ApprovalWorkflowService


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/show_leave.py <leave_id>")
        sys.exit(1)
    leave_id = int(sys.argv[1])
    try:
        lr = LeaveRequest.objects.select_related('employee__affiliate', 'employee__department__affiliate').get(id=leave_id)
    except LeaveRequest.DoesNotExist:
        print(f"LeaveRequest {leave_id} not found")
        return
    emp = lr.employee
    emp_aff = getattr(getattr(emp, 'affiliate', None), 'name', None)
    dept_aff = getattr(getattr(getattr(emp, 'department', None), 'affiliate', None), 'name', None)
    expected_ceo = ApprovalRoutingService.get_ceo_for_employee(emp)
    expected_label = f"{expected_ceo.id}:{expected_ceo.get_full_name()}" if expected_ceo else None
    print(f"lr#{lr.id} status={lr.status} employee={emp.get_full_name()} <{emp.email}> role={emp.role} aff={emp_aff} dept_aff={dept_aff} expected_ceo={expected_label}")
    # Who can approve
    User = get_user_model()
    ceos = list(User.objects.filter(role='ceo', is_active=True))
    for c in ceos:
        can = ApprovalWorkflowService.can_user_approve(lr, c)
        print(f"  CEO {c.id} {c.get_full_name()} aff={getattr(getattr(c,'affiliate',None),'name',None)} can_approve={can}")

if __name__ == '__main__':
    main()
