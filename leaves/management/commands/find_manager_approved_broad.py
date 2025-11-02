from django.core.management.base import BaseCommand
import json

class Command(BaseCommand):
    help = 'Broad search for manager_approved leave requests by manager jmankoe or employee name george'

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        from leaves.models import LeaveRequest
        from leaves.services import ApprovalWorkflowService
        from django.db.models import Q

        User = get_user_model()

        qs = LeaveRequest.objects.filter(status='manager_approved')
        qs = qs.filter(
            Q(manager_approved_by__username__icontains='jmankoe') |
            Q(employee__first_name__icontains='george') |
            Q(employee__last_name__icontains='george')
        )

        out = []
        for lr in qs.select_related('employee','employee__department','employee__affiliate'):
            handler = ApprovalWorkflowService.get_handler(lr)
            next_approver = ApprovalWorkflowService.get_next_approver(lr)
            out.append({
                'id': lr.id,
                'employee': {'id': lr.employee.id, 'name': lr.employee.get_full_name(), 'email': lr.employee.email},
                'start_date': lr.start_date.isoformat(), 'end_date': lr.end_date.isoformat(),
                'created_at': lr.created_at.isoformat() if lr.created_at else None,
                'manager_approved_by': lr.manager_approved_by.get_full_name() if lr.manager_approved_by else None,
                'manager_approval_date': lr.manager_approval_date.isoformat() if lr.manager_approval_date else None,
                'handler_class': handler.__class__.__name__,
                'next_approver': {'id': getattr(next_approver,'id',None), 'name': getattr(next_approver,'get_full_name',lambda:None)() if next_approver else None, 'email': getattr(next_approver,'email',None) if next_approver else None},
            })

        self.stdout.write(json.dumps({'count': len(out), 'results': out}, indent=2, default=str))
