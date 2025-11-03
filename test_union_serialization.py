import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from leaves.models import LeaveRequest
from leaves.serializers import LeaveRequestListSerializer
from django.db.models import Q

print("=" * 80)
print("TESTING UNION SERIALIZATION")
print("=" * 80)

# Test the exact logic from the view
print("\n1. Building Merban queryset (manager_approved, excluding SDSL/SBL):")
merban_qs = LeaveRequest.objects.filter(status='manager_approved').exclude(
    Q(employee__department__affiliate__name__in=['SDSL', 'SBL']) |
    Q(employee__affiliate__name__in=['SDSL', 'SBL'])
).exclude(employee__role='admin')
print(f"   Merban count: {merban_qs.count()}")

print("\n2. Building CEO approved queryset:")
ceo_approved_qs = LeaveRequest.objects.filter(status='ceo_approved').exclude(employee__role='admin')
print(f"   CEO approved count: {ceo_approved_qs.count()}")

print("\n3. Creating UNION:")
try:
    union_qs = merban_qs.union(ceo_approved_qs)
    print(f"   Union count: {union_qs.count()}")
    print("   Union created successfully!")
    
    print("\n4. Testing serialization with LeaveRequestListSerializer:")
    try:
        serializer = LeaveRequestListSerializer(union_qs, many=True)
        data = serializer.data
        print(f"   Serialization successful! Got {len(data)} items")
        
        # Check if fields are present
        if data:
            print(f"\n5. Sample item fields:")
            sample = data[0]
            print(f"   Keys: {list(sample.keys())}")
            print(f"   Has employee_department_affiliate: {'employee_department_affiliate' in sample}")
            print(f"   Has employee_department_id: {'employee_department_id' in sample}")
            
    except Exception as e:
        print(f"   ❌ SERIALIZATION FAILED: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f"   ❌ UNION FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n6. ALTERNATIVE: Using list() instead of union():")
try:
    from itertools import chain
    combined = list(chain(merban_qs, ceo_approved_qs))
    print(f"   Combined list count: {len(combined)}")
    
    serializer = LeaveRequestListSerializer(combined, many=True)
    data = serializer.data
    print(f"   Serialization successful! Got {len(data)} items")
    
except Exception as e:
    print(f"   ❌ FAILED: {e}")

print("\n" + "=" * 80)
