from django.contrib.auth import get_user_model
from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService, ApprovalRoutingService

User = get_user_model()

ceo = User.objects.filter(email__iexact='sblceo@umbcapital.com').first()
print(f"SBL CEO: {ceo} affiliate={getattr(ceo,'affiliate',None)}")

qs = LeaveRequest.objects.select_related('employee__department__affiliate','employee__affiliate').filter(status='pending')
print(f"Pending count: {qs.count()}")

for lr in qs:
    emp = lr.employee
    aff = emp.affiliate or (emp.department.affiliate if getattr(emp,'department',None) else None)
    aff_name = (getattr(aff,'name','') or '').upper()
    if aff_name == 'SBL':
        expected = ApprovalRoutingService.get_ceo_for_employee(emp)
        handler = ApprovalWorkflowService.get_handler(lr)
        can = handler.can_approve(ceo, lr.status) if ceo else False
        print(f"LR#{lr.id} emp={emp.email} role={getattr(emp,'role',None)} aff={aff_name} status={lr.status} expected_ceo={getattr(expected,'email',None)} can_winslow_approve={can}")
