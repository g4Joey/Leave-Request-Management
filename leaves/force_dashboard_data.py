"""
Simple API endpoint to force dashboard data creation
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from leaves.models import LeaveBalance, LeaveType
from users.models import CustomUser


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def force_create_dashboard_data(request):
    """Force create dashboard data if missing"""
    try:
        current_year = timezone.now().year
        
        users = CustomUser.objects.filter(is_active=True, is_active_employee=True)
        leave_types = LeaveType.objects.filter(is_active=True)
        
        if not users.exists() or not leave_types.exists():
            return Response({
                'status': 'error',
                'message': 'No users or leave types found'
            })
        
        # Default entitlements
        entitlements = {
            'Annual Leave': 21,
            'Sick Leave': 10,
            'Casual Leave': 5,
            'Maternity Leave': 90,
            'Paternity Leave': 10,
            'Study Leave': 5
        }
        
        created_count = 0
        for user in users:
            for leave_type in leave_types:
                entitled_days = entitlements.get(leave_type.name, 21)
                
                _, created = LeaveBalance.objects.get_or_create(
                    employee=user,
                    leave_type=leave_type,
                    year=current_year,
                    defaults={
                        'entitled_days': entitled_days,
                        'used_days': 0,
                        'pending_days': 0
                    }
                )
                if created:
                    created_count += 1
        
        return Response({
            'status': 'success',
            'created_count': created_count,
            'total_balances': LeaveBalance.objects.filter(year=current_year).count()
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        })