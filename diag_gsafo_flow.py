from django.contrib.auth import get_user_model
from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService

User = get_user_model()

user = User.objects.filter(email__icontains='gsafo').first()
print('User:', user, 'role=', getattr(user,'role',None))
if hasattr(user,'department'):
    dep = user.department
    print('Department:', dep, 'HOD:', getattr(dep,'hod',None))
    print('Manager:', getattr(user,'manager',None))

req = LeaveRequest.objects.filter(employee=user).order_by('-created_at').first()
print('Latest request:', req, 'status=', getattr(req,'status',None))
if req:
    handler = ApprovalWorkflowService.get_handler(req)
    print('Handler:', handler.__class__.__name__)
    flow = handler.get_approval_flow()
    print('Flow mapping:', flow)
    print('Next status suggestion:', handler.get_next_status(req.status))
