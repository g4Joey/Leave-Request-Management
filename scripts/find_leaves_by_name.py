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

from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService, ApprovalRoutingService


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/find_leaves_by_name.py <name-fragment>")
        sys.exit(1)
    query = sys.argv[1]
    User = get_user_model()
    users = list(User.objects.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query)))
    if not users:
        print(f"No users found matching '{query}'.")
        return
    print(f"Found {len(users)} user(s) matching '{query}':")
    for u in users:
        aff = getattr(getattr(u, 'affiliate', None), 'name', None)
        dept_aff = getattr(getattr(getattr(u, 'department', None), 'affiliate', None), 'name', None)
        print(f"- {u.id}: {u.get_full_name()} <{u.email}> role={u.role} affiliate={aff} dept_aff={dept_aff}")
        reqs = list(LeaveRequest.objects.filter(employee=u).order_by('-created_at'))
        if not reqs:
            print("  (no leave requests)")
            continue
        for lr in reqs:
            expected_ceo = ApprovalRoutingService.get_ceo_for_employee(u)
            expected_ceo_label = f"{expected_ceo.id}:{expected_ceo.get_full_name()}" if expected_ceo else None
            print(f"  lr#{lr.id}: status={lr.status} next_stage={lr.current_approval_stage} expected_ceo={expected_ceo_label}")


if __name__ == '__main__':
    main()
