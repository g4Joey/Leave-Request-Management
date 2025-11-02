from datetime import datetime, timedelta
import json
from django.utils import timezone
from django.contrib.auth import get_user_model
from leaves.models import LeaveRequest, LeaveType
from leaves.services import ApprovalWorkflowService

User = get_user_model()

def dt(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")

# Search parameters based on your description
start_date = datetime(2025,11,11).date()
end_date = datetime(2025,11,12).date()
status = 'manager_approved'
leave_type_name = 'Annual'
created_after = datetime(2025,10,30,0,0,0)
created_before = datetime(2025,10,30,23,59,59)

qs = LeaveRequest.objects.filter(status=status, start_date=start_date, end_date=end_date)
# narrow by leave type name if present
lt = LeaveType.objects.filter(name__icontains(leave_type_name).all())
if lt.exists():
    qs = qs.filter(leave_type__in=lt)

# narrow by created_at window (if using created_at field)
qs = qs.filter(created_at__gte=created_after, created_at__lte=created_before)

results = []
for lr in qs.select_related('employee','employee__department','employee__affiliate'):
    handler = ApprovalWorkflowService.get_handler(lr)
    next_approver = ApprovalWorkflowService.get_next_approver(lr)
    hr_user = User.objects.filter(role='hr', is_active=True).first()
    ceo_user = User.objects.filter(role='ceo', is_active=True).first()
    results.append({
        'id': lr.id,
        'employee': {'id': lr.employee.id, 'name': lr.employee.get_full_name(), 'email': lr.employee.email},
        'status': lr.status,
        'created_at': lr.created_at.isoformat() if lr.created_at else None,
        'manager_approved_by': lr.manager_approved_by.get_full_name() if lr.manager_approved_by else None,
        'manager_approval_date': lr.manager_approval_date.isoformat() if lr.manager_approval_date else None,
        'hr_approved_by': lr.hr_approved_by.get_full_name() if lr.hr_approved_by else None,
        'hr_approval_date': lr.hr_approval_date.isoformat() if lr.hr_approval_date else None,
        'ceo_approved_by': lr.ceo_approved_by.get_full_name() if lr.ceo_approved_by else None,
        'ceo_approval_date': lr.ceo_approval_date.isoformat() if lr.ceo_approval_date else None,
        'employee_department_affiliate': (lr.employee.department.affiliate.name if getattr(lr.employee, 'department', None) and getattr(lr.employee.department, 'affiliate', None) else None),
        'employee_affiliate': (lr.employee.affiliate.name if getattr(lr.employee, 'affiliate', None) else None),
        'handler_class': handler.__class__.__name__,
        'next_approver': {'id': getattr(next_approver,'id',None), 'name': getattr(next_approver,'get_full_name',lambda:None)() if next_approver else None, 'email': getattr(next_approver,'email',None) if next_approver else None},
        'can_hr_approve_now': bool(hr_user and ApprovalWorkflowService.can_user_approve(lr, hr_user)),
        'can_ceo_approve_now': bool(ceo_user and ApprovalWorkflowService.can_user_approve(lr, ceo_user)),
    })

print(json.dumps({'count': len(results), 'results': results}, indent=2, default=str))
