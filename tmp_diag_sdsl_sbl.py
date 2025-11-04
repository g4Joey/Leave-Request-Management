from users.models import CustomUser
from leaves.models import LeaveRequest
from leaves.services import ApprovalRoutingService, ApprovalWorkflowService
from django.contrib.auth import get_user_model

User = get_user_model()

def find_users(q: str):
    qs = CustomUser.objects.none()
    for f in ['email__icontains','first_name__icontains','last_name__icontains','username__icontains']:
        qs = qs | CustomUser.objects.filter(**{f:q})
    return qs.distinct()

print("[diag] Starting SDSL/SBL diagnostics for 'Esther' and 'asanunu' ...")
for key in ['esther','asanunu']:
    users=list(find_users(key))
    print(f"--- Query '{key}' matched {len(users)} user(s)")
    for u in users:
        aff = getattr(getattr(u,'affiliate',None),'name',None)
        dept = getattr(getattr(u,'department',None),'name',None)
        mgr = getattr(getattr(u,'manager',None),'email',None)
        print(f"  user id={u.id} email={u.email} role={u.role} affiliate={aff} dept={dept} manager={mgr}")
        lr = LeaveRequest.objects.filter(employee=u).order_by('-created_at').first()
        if lr:
            emp_aff = ApprovalRoutingService.get_employee_affiliate_name(u)
            ceo = ApprovalRoutingService.get_ceo_for_employee(u)
            print(f"    latest lr id={lr.id} status={lr.status} emp_aff='{emp_aff}' ceo_email={getattr(ceo,'email',None)}")
            if ceo:
                print(f"    CEO can approve now? {ApprovalWorkflowService.can_user_approve(lr, ceo)}")
        else:
            print("    no leave requests found")

# Scan future-proofing: ensure all SDSL/SBL staff will route to their CEO
issues = []
all_staff = CustomUser.objects.filter(is_active=True).exclude(role__in=['admin','hr','manager','hod'])
for u in all_staff:
    aff_name = ApprovalRoutingService.get_employee_affiliate_name(u)
    if aff_name.upper() in ['SDSL','SBL']:
        ceo = ApprovalRoutingService.get_ceo_for_employee(u)
        if not ceo:
            issues.append((u.id, u.email, aff_name, 'NO_CEO_FOUND'))
        else:
            # Check a synthetic pending request approvalability by CEO by simulating status 'pending'
            lr = LeaveRequest.objects.filter(employee=u).order_by('-created_at').first()
            if lr:
                # Temporarily examine approval on current status (should be pending in new flow)
                can = ApprovalWorkflowService.can_user_approve(lr, ceo)
                if lr.status == 'pending' and not can:
                    issues.append((u.id, u.email, aff_name, 'CEO_CANNOT_APPROVE_PENDING'))

if issues:
    print("\n[diag] Potential routing issues detected for the following users:")
    for row in issues:
        print("  id=%s email=%s affiliate=%s issue=%s" % row)
else:
    print("\n[diag] No routing issues detected for SDSL/SBL staff.")
