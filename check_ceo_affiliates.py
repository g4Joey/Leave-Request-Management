"""Check CEO affiliate settings and test approval permissions"""
from django.contrib.auth import get_user_model
from users.models import Affiliate, Department
from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService, ApprovalRoutingService

User = get_user_model()

print("\n=== CEO Affiliate Check ===")
ceos = User.objects.filter(role='ceo', is_active=True)
print(f"Found {ceos.count()} active CEOs:")
for ceo in ceos:
    print(f"  - {ceo.email} ({ceo.get_full_name()})")
    print(f"    Affiliate: {ceo.affiliate}")
    print(f"    Department: {ceo.department}")
    if ceo.affiliate:
        print(f"    Affiliate name: {ceo.affiliate.name}")

print("\n=== Affiliate Names ===")
affiliates = Affiliate.objects.all()
for aff in affiliates:
    print(f"  - {aff.name}")

print("\n=== Test Approval Routing ===")
# Find a test request
test_requests = LeaveRequest.objects.filter(status='hr_approved')[:3]
if test_requests.exists():
    for req in test_requests:
        print(f"\nRequest #{req.id} by {req.employee.email}")
        print(f"  Employee affiliate: {req.employee.affiliate}")
        print(f"  Employee department: {req.employee.department}")
        if req.employee.department:
            print(f"  Department affiliate: {req.employee.department.affiliate}")
        
        expected_ceo = ApprovalRoutingService.get_ceo_for_employee(req.employee)
        print(f"  Expected CEO: {expected_ceo.email if expected_ceo else 'None'}")
        
        handler = ApprovalWorkflowService.get_handler(req)
        print(f"  Handler: {handler.__class__.__name__}")
        print(f"  Current status: {req.status}")
        
        # Test each CEO
        for ceo in ceos:
            can_approve = handler.can_approve(ceo, req.status)
            print(f"  Can {ceo.email} approve? {can_approve}")
else:
    print("No hr_approved requests to test with")

print("\n=== HR Department Check ===")
hr_dept = Department.objects.filter(name__iexact='HR & Admin').first()
if hr_dept:
    print(f"HR & Admin department found:")
    print(f"  - Affiliate: {hr_dept.affiliate}")
    print(f"  - HOD: {hr_dept.hod}")
else:
    print("HR & Admin department not found")

print("\n=== Benjamin Ackah (Merban CEO) Check ===")
benjamin = User.objects.filter(email='ceo@umbcapital.com').first()
if benjamin:
    print(f"Found Benjamin Ackah:")
    print(f"  - Email: {benjamin.email}")
    print(f"  - Name: {benjamin.get_full_name()}")
    print(f"  - Role: {benjamin.role}")
    print(f"  - Affiliate: {benjamin.affiliate}")
    print(f"  - Department: {benjamin.department}")
    print(f"  - Is active: {benjamin.is_active}")
else:
    print("Benjamin Ackah not found")
