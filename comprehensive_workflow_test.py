import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService
from leaves.serializers import LeaveRequestSerializer

print("=" * 80)
print("COMPREHENSIVE WORKFLOW VERIFICATION")
print("=" * 80)

test_cases = [
    {
        'name': 'Merban Staff',
        'filters': {'role': 'staff', 'affiliate__name': 'Merban Capital'},
        'expected_flow': {'pending': 'manager', 'manager_approved': 'hr', 'hr_approved': 'ceo'},
        'expected_pending_display': 'Pending Manager Approval'
    },
    {
        'name': 'Merban Manager',
        'filters': {'role': 'manager', 'affiliate__name': 'Merban Capital'},
        'expected_flow': {'pending': 'hr', 'hr_approved': 'ceo'},
        'expected_pending_display': 'Pending HR Approval'
    },
    {
        'name': 'Merban HR',
        'filters': {'role': 'hr', 'affiliate__name': 'Merban Capital'},
        'expected_flow': {'pending': 'hr', 'hr_approved': 'ceo'},
        'expected_pending_display': 'Pending HR Approval'
    },
    {
        'name': 'SDSL Staff',
        'filters': {'role': 'staff', 'affiliate__name': 'SDSL'},
        'expected_flow': {'pending': 'ceo', 'ceo_approved': 'hr'},
        'expected_pending_display': 'Pending CEO Approval'
    },
    {
        'name': 'SDSL CEO',
        'filters': {'role': 'ceo', 'affiliate__name': 'SDSL'},
        'expected_flow': {'pending': 'hr'},
        'expected_pending_display': 'Pending HR Approval'
    },
]

all_passed = True

for test in test_cases:
    print(f"\n{'='*80}")
    print(f"Testing: {test['name']}")
    print('='*80)
    
    user = CustomUser.objects.filter(**test['filters']).first()
    
    if not user:
        print(f"❌ FAIL: No user found matching filters {test['filters']}")
        all_passed = False
        continue
    
    print(f"✓ User: {user.get_full_name()} ({user.email})")
    print(f"  Role: {user.role}")
    print(f"  Affiliate: {user.affiliate.name if user.affiliate else 'None'}")
    print(f"  Department: {user.department.name if user.department else 'None'}")
    
    # Create test request
    test_request = LeaveRequest(employee=user, status='pending')
    handler = ApprovalWorkflowService.get_handler(test_request)
    flow = handler.get_approval_flow()
    
    print(f"\n  Approval Flow:")
    for status, next_role in flow.items():
        print(f"    {status} → {next_role}")
    
    # Check flow matches expected
    if flow != test['expected_flow']:
        print(f"\n  ❌ FAIL: Flow mismatch!")
        print(f"    Expected: {test['expected_flow']}")
        print(f"    Got: {flow}")
        all_passed = False
    else:
        print(f"  ✓ Flow matches expected")
    
    # Check dynamic status display
    display = test_request.get_dynamic_status_display()
    print(f"\n  Dynamic Status Display: '{display}'")
    
    if display != test['expected_pending_display']:
        print(f"  ❌ FAIL: Status display mismatch!")
        print(f"    Expected: '{test['expected_pending_display']}'")
        print(f"    Got: '{display}'")
        all_passed = False
    else:
        print(f"  ✓ Status display matches expected")

print(f"\n{'='*80}")
print("SUMMARY")
print('='*80)

if all_passed:
    print("\n✅ ALL TESTS PASSED!")
else:
    print("\n❌ SOME TESTS FAILED - Review output above")

print("\n" + "="*80)
print("CHECKING CEO DEPARTMENTS")
print("="*80)

ceos = CustomUser.objects.filter(role='ceo')
print(f"\nTotal CEOs: {ceos.count()}")

ceo_issues = []
for ceo in ceos:
    dept_name = ceo.department.name if ceo.department else None
    print(f"\n{ceo.get_full_name()} ({ceo.affiliate.name if ceo.affiliate else 'No Affiliate'})")
    print(f"  Department: {dept_name or 'None (correct)'}")
    
    if dept_name:
        ceo_issues.append(f"{ceo.get_full_name()} has department: {dept_name}")
        print(f"  ⚠️ WARNING: CEO should not have a department!")

if ceo_issues:
    print(f"\n❌ CEO DEPARTMENT ISSUES FOUND:")
    for issue in ceo_issues:
        print(f"  - {issue}")
else:
    print(f"\n✅ All CEOs have no department (correct)")

print("\n" + "="*80)
