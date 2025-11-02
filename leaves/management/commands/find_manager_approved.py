from django.core.management.base import BaseCommand
from datetime import datetime
import json

class Command(BaseCommand):
    help = 'Find leave requests with status manager_approved created on 2025-10-30 and print diagnostics'

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        from leaves.models import LeaveRequest
        from leaves.services import ApprovalWorkflowService

        User = get_user_model()
        date_start = datetime(2025,10,30,0,0,0)
        date_end = datetime(2025,10,30,23,59,59)

        qs = LeaveRequest.objects.filter(status='manager_approved', created_at__gte=date_start, created_at__lte=date_end)

        out = []
        for lr in qs.select_related('employee','employee__department','employee__affiliate'):
            handler = ApprovalWorkflowService.get_handler(lr)
            next_approver = ApprovalWorkflowService.get_next_approver(lr)
            out.append({
                'id': lr.id,
                'employee': {'id': lr.employee.id, 'name': lr.employee.get_full_name(), 'email': lr.employee.email},
                'start_date': lr.start_date.isoformat(), 'end_date': lr.end_date.isoformat(),
                'manager_approved_by': lr.manager_approved_by.get_full_name() if lr.manager_approved_by else None,
                'manager_approval_date': lr.manager_approval_date.isoformat() if lr.manager_approval_date else None,
                'handler_class': handler.__class__.__name__,
                'next_approver': {'id': getattr(next_approver,'id',None), 'name': getattr(next_approver,'get_full_name',lambda:None)() if next_approver else None, 'email': getattr(next_approver,'email',None) if next_approver else None},
                'employee_affiliate': (lr.employee.affiliate.name if getattr(lr.employee, 'affiliate', None) else None),
                'employee_department_affiliate': (lr.employee.department.affiliate.name if getattr(lr.employee, 'department', None) and getattr(lr.employee.department, 'affiliate', None) else None),
            })

        self.stdout.write(json.dumps({'count': len(out), 'results': out}, indent=2, default=str))
