"""Check request #18 status and history"""
from leaves.models import LeaveRequest

req = LeaveRequest.objects.get(id=18)
print(f"\nRequest #18 Details:")
print(f"  Employee: {req.employee.get_full_name()} ({req.employee.email})")
print(f"  Employee affiliate: {req.employee.affiliate}")
print(f"  Status: {req.status}")
print(f"  Current approval stage: {req.current_approval_stage}")
print(f"\nApproval History:")
print(f"  Manager approved by: {req.manager_approved_by}")
print(f"  Manager approval date: {req.manager_approval_date}")
print(f"  HR approved by: {req.hr_approved_by}")
print(f"  HR approval date: {req.hr_approval_date}")
print(f"  CEO approved by: {req.ceo_approved_by}")
print(f"  CEO approval date: {req.ceo_approval_date}")

print("\n⚠️ This is the problem:")
print("For SBL/SDSL employees, the flow should be: pending → CEO → HR (final)")
print("But this request is in 'hr_approved' status, which is the Merban flow.")
print("\nThis request was probably created/approved before the new workflow was implemented.")
print("It should be in 'ceo_approved' status (waiting for HR final approval) or 'pending' (waiting for CEO).")
