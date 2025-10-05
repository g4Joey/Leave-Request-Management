"""
Debug views for production troubleshooting
"""
from django.http import JsonResponse
from django.core.management import call_command
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from users.models import CustomUser
from leaves.models import LeaveBalance, LeaveType
from django.utils import timezone
import io
import sys

@csrf_exempt
@require_http_methods(["POST"])
def debug_fix_production_data(request):
    """Manually trigger the fix_production_data command and return output"""
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Capture command output
    output = io.StringIO()
    try:
        call_command('fix_production_data', stdout=output)
        command_output = output.getvalue()
        
        # Get current stats
        current_year = timezone.now().year
        employees = CustomUser.objects.filter(is_active=True, is_active_employee=True)
        balances = LeaveBalance.objects.filter(year=current_year)
        leave_types = LeaveType.objects.filter(is_active=True)
        
        return JsonResponse({
            'status': 'success',
            'command_output': command_output,
            'stats': {
                'active_employees': employees.count(),
                'leave_balances': balances.count(),
                'active_leave_types': leave_types.count(),
                'current_year': current_year,
            }
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'command_output': output.getvalue()
        })
    finally:
        output.close()

@require_http_methods(["GET"])
def debug_production_stats(request):
    """Get production database stats"""
    current_year = timezone.now().year
    employees = CustomUser.objects.filter(is_active=True, is_active_employee=True)
    balances = LeaveBalance.objects.filter(year=current_year)
    leave_types = LeaveType.objects.filter(is_active=True)
    managers = CustomUser.objects.filter(role='manager')
    
    # Sample balances
    sample_balances = []
    for balance in balances.select_related('employee', 'leave_type')[:10]:
        sample_balances.append({
            'employee': balance.employee.username,
            'leave_type': balance.leave_type.name,
            'entitled': balance.entitled_days,
            'used': balance.used_days,
            'remaining': balance.remaining_days
        })
    
    return JsonResponse({
        'current_year': current_year,
        'stats': {
            'active_employees': employees.count(),
            'leave_balances': balances.count(),
            'active_leave_types': leave_types.count(),
            'managers': managers.count(),
        },
        'employees': [{'username': emp.username, 'role': emp.role} for emp in employees],
        'leave_types': [{'name': lt.name, 'is_active': lt.is_active} for lt in leave_types],
        'managers': [{'username': mgr.username} for mgr in managers],
        'sample_balances': sample_balances
    })