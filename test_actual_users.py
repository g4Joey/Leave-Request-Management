import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from leaves.models import LeaveRequest
from leaves.services import ApprovalWorkflowService

print("=" * 80)
print("TESTING WITH ACTUAL USERS IN DATABASE")
print("=" * 80)

# Get jmankoe (manager)
jmankoe = CustomUser.objects.filter(email__icontains='jmankoe').first()
if jmankoe:
    print(f"\n1. MANAGER TEST: {jmankoe.get_full_name()}")
    print(f"   Email: {jmankoe.email}")
    print(f"   Role: {jmankoe.role}")
    print(f"   Affiliate: {jmankoe.affiliate.name if jmankoe.affiliate else 'None'}")
    print(f"   Department: {jmankoe.department.name if jmankoe.department else 'None'}")
    
    test_req = LeaveRequest(employee=jmankoe, status='pending')
    handler = ApprovalWorkflowService.get_handler(test_req)
    flow = handler.get_approval_flow()
    
    print(f"\n   Expected: Manager/HR goes pending → hr → ceo")
    print(f"   Actual Flow: {flow}")
    print(f"   Dynamic Display: '{test_req.get_dynamic_status_display()}'")
    
    if flow == {'pending': 'hr', 'hr_approved': 'ceo'}:
        print(f"   ✅ PASS: Manager flow correct")
    else:
        print(f"   ❌ FAIL: Manager flow incorrect")

# Test with a staff member
staff_users = CustomUser.objects.exclude(role__in=['ceo', 'admin', 'manager', 'hr', 'hod']).filter(affiliate__name='MERBAN CAPITAL')
if staff_users.exists():
    staff = staff_users.first()
    print(f"\n2. STAFF TEST: {staff.get_full_name()}")
    print(f"   Email: {staff.email}")
    print(f"   Role: {staff.role}")
    print(f"   Affiliate: {staff.affiliate.name if staff.affiliate else 'None'}")
    
    test_req = LeaveRequest(employee=staff, status='pending')
    handler = ApprovalWorkflowService.get_handler(test_req)
    flow = handler.get_approval_flow()
    
    print(f"\n   Expected: Staff goes pending → manager → hr → ceo")
    print(f"   Actual Flow: {flow}")
    print(f"   Dynamic Display: '{test_req.get_dynamic_status_display()}'")
    
    if flow == {'pending': 'manager', 'manager_approved': 'hr', 'hr_approved': 'ceo'}:
        print(f"   ✅ PASS: Staff flow correct")
    else:
        print(f"   ❌ FAIL: Staff flow incorrect")
else:
    print(f"\n2. STAFF TEST: No staff users found in Merban Capital")

# Test CEO
sdsl_ceo = CustomUser.objects.filter(role='ceo', affiliate__name='SDSL').first()
if sdsl_ceo:
    print(f"\n3. CEO TEST (SDSL): {sdsl_ceo.get_full_name()}")
    print(f"   Email: {sdsl_ceo.email}")
    print(f"   Affiliate: {sdsl_ceo.affiliate.name if sdsl_ceo.affiliate else 'None'}")
    print(f"   Department: {sdsl_ceo.department.name if sdsl_ceo.department else 'None'}")
    
    test_req = LeaveRequest(employee=sdsl_ceo, status='pending')
    handler = ApprovalWorkflowService.get_handler(test_req)
    flow = handler.get_approval_flow()
    
    print(f"\n   Expected: CEO skips CEO stage, goes pending → hr")
    print(f"   Actual Flow: {flow}")
    print(f"   Dynamic Display: '{test_req.get_dynamic_status_display()}'")
    
    if flow == {'pending': 'hr'}:
        print(f"   ✅ PASS: CEO flow correct")
    else:
        print(f"   ❌ FAIL: CEO flow incorrect")

# Show all users for reference
print("\n" + "=" * 80)
print("ALL ACTIVE USERS")
print("=" * 80)

all_users = CustomUser.objects.filter(is_active=True).order_by('affiliate__name', 'role')
for user in all_users:
    affiliate = user.affiliate.name if user.affiliate else 'No Affiliate'
    dept = user.department.name if user.department else 'No Dept'
    print(f"{user.get_full_name():30} | {user.role:15} | {affiliate:20} | {dept}")
