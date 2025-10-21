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

@csrf_exempt
def debug_api_functionality(request):
    """Debug all API functionality issues"""
    from django.contrib.auth import get_user_model
    from leaves.models import LeaveRequest
    
    User = get_user_model()
    current_year = timezone.now().year
    
    # Check all users and their data
    users_data = []
    for user in User.objects.filter(is_active=True):
        # Check leave balances
        balances = LeaveBalance.objects.filter(employee=user, year=current_year)
        
        # Check leave requests
        requests = LeaveRequest.objects.filter(employee=user)
        
        users_data.append({
            'user_id': getattr(user, 'id', 'unknown'),
            'username': user.username,
            'email': user.email,
            'role': getattr(user, 'role', 'unknown'),
            'is_active_employee': getattr(user, 'is_active_employee', 'unknown'),
            'leave_balances_count': balances.count(),
            'leave_requests_count': requests.count(),
            'leave_balances': [
                {
                    'leave_type': b.leave_type.name,
                    'entitled': b.entitled_days,
                    'used': b.used_days,
                    'remaining': b.remaining_days
                } for b in balances
            ],
            'recent_requests': [
                {
                    'id': getattr(r, 'id', 'unknown'),
                    'status': r.status,
                    'leave_type': r.leave_type.name,
                    'start_date': str(r.start_date),
                    'end_date': str(r.end_date)
                } for r in requests.order_by('-created_at')[:3]
            ]
        })
    
    return JsonResponse({
        'timestamp': timezone.now().isoformat(),
        'current_year': current_year,
        'total_users': User.objects.filter(is_active=True).count(),
        'total_balances': LeaveBalance.objects.filter(year=current_year).count(),
        'total_requests': LeaveRequest.objects.count(),
        'users_data': users_data
    })

@csrf_exempt
@require_http_methods(["POST"])
def debug_fix_all_user_references(request):
    """Manually trigger the comprehensive user reference fix command and return output"""
    # Capture command output
    output = io.StringIO()
    try:
        call_command('fix_all_user_references', stdout=output)
        command_output = output.getvalue()
        
        # Get current stats after fix
        current_year = timezone.now().year
        from django.contrib.auth import get_user_model
        from leaves.models import LeaveRequest
        User = get_user_model()
        
        employees = User.objects.filter(is_active=True)
        balances = LeaveBalance.objects.filter(year=current_year)
        requests = LeaveRequest.objects.all()
        leave_types = LeaveType.objects.filter(is_active=True)
        
        return JsonResponse({
            'status': 'success',
            'command_output': command_output,
            'stats_after_fix': {
                'total_users': employees.count(),
                'leave_balances': balances.count(),
                'leave_requests': requests.count(),
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

@csrf_exempt
@require_http_methods(["POST"])
def debug_quick_user_fix(request):
    """Manually trigger the quick_user_fix command and return output"""
    # Capture command output
    output = io.StringIO()
    try:
        call_command('quick_user_fix', stdout=output)
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

@csrf_exempt
@require_http_methods(["POST"])
def debug_fix_user_mismatches(request):
    """Manually trigger the fix_user_mismatches command and return output"""
    # Capture command output
    output = io.StringIO()
    try:
        call_command('fix_user_mismatches', stdout=output)
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

@csrf_exempt
@require_http_methods(["POST"])
def debug_setup_fresh_database(request):
    """Manually trigger the setup_fresh_database command and return output"""
    # Capture command output
    output = io.StringIO()
    try:
        call_command('setup_fresh_database', stdout=output)
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
    import os
    current_year = timezone.now().year
    employees = CustomUser.objects.filter(is_active=True, is_active_employee=True)
    balances = LeaveBalance.objects.filter(year=current_year)
    leave_types = LeaveType.objects.filter(is_active=True)
    hods = CustomUser.objects.filter(role='hod')
    
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
        'environment': {
            'SETUP_FRESH_DATABASE': os.getenv('SETUP_FRESH_DATABASE', 'NOT_SET'),
            'RUN_FIX_PRODUCTION_DATA': os.getenv('RUN_FIX_PRODUCTION_DATA', 'NOT_SET'),
            'DATABASE_URL': 'SET' if os.getenv('DATABASE_URL') else 'NOT_SET',
            'DEBUG': os.getenv('DEBUG', 'NOT_SET'),
        },
        'stats': {
            'active_employees': employees.count(),
            'leave_balances': balances.count(),
            'active_leave_types': leave_types.count(),
            'hods': hods.count(),
        },
        'employees': [{'username': emp.username, 'role': emp.role} for emp in employees],
        'leave_types': [{'name': lt.name, 'is_active': lt.is_active} for lt in leave_types],
    'hods': [{'username': hod.username} for hod in hods],
        'sample_balances': sample_balances
    })