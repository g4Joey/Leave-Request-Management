"""
Views for the main leave_management project.
"""
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)

def api_health(request):
    """Lightweight API health endpoint that does not touch the database."""
    return JsonResponse({
        'status': 'ok',
        'message': 'API is responding'
    })

def api_health_db(request):
    """API health endpoint that verifies database connectivity explicitly."""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
        return JsonResponse({'status': 'ok', 'database': 'connected', 'result': row[0] if row else None})
    except Exception as e:
        logger.error(f"/api/health/db failed: {e}")
        return JsonResponse({'status': 'error', 'database': 'disconnected', 'error': str(e)}, status=500)

def health_check(request):
    """Simple health check endpoint for deployment monitoring."""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        db_status = "disconnected"
    
    return JsonResponse({
        'status': 'ok',
        'message': 'Leave Management System is running',
        'database': db_status,
    })

def server_error(request, template_name='500.html'):
    """
    500 error handler that returns JSON for API requests
    """
    if 'api' in request.path:
        return JsonResponse({'error': 'Internal server error'}, status=500)
    # For HTML requests, use default error page
    return HttpResponse("Internal Server Error", status=500)


def debug_dashboard_data(request):
    """Debug endpoint to check dashboard data for authenticated users"""
    from rest_framework.decorators import api_view, permission_classes
    from rest_framework.permissions import IsAuthenticated
    from rest_framework.response import Response
    from leaves.models import LeaveBalance, LeaveType
    from django.utils import timezone
    
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    current_year = timezone.now().year
    user = request.user
    
    # Get user's leave balances
    balances = LeaveBalance.objects.filter(employee=user, year=current_year)
    
    # Get all active leave types for comparison
    leave_types = LeaveType.objects.filter(is_active=True)
    
    debug_data = {
        'user_info': {
            'username': user.username,
            'full_name': user.get_full_name(),
            'is_active': user.is_active,
            'is_active_employee': getattr(user, 'is_active_employee', None),
        },
        'year': current_year,
        'leave_types_count': leave_types.count(),
        'leave_types': [{'id': getattr(lt, 'id'), 'name': lt.name} for lt in leave_types],
        'balances_count': balances.count(),
        'balances': [
            {
                'leave_type': balance.leave_type.name,
                'entitled_days': balance.entitled_days,
                'used_days': balance.used_days,
                'pending_days': balance.pending_days,
                'remaining_days': balance.remaining_days,
            }
            for balance in balances
        ]
    }
    
    return JsonResponse(debug_data)




def not_found(request, exception, template_name='404.html'):
    """
    404 error handler that returns JSON for API requests
    and HTML for regular requests.
    """
    if request.path.startswith('/api/'):
        return JsonResponse({
            'error': 'Not found',
            'message': 'The requested endpoint does not exist.'
        }, status=404)
    
    # For non-API requests, you could render an HTML template
    from django.shortcuts import render
    return render(request, '404.html', status=404)

@csrf_exempt
def debug_static_files(request):
    """Return a JSON list of files present in STATIC_ROOT and frontend build static dir.

    This endpoint is intended for short-term debugging in production and is
    protected by a simple secret header to avoid exposing file lists publicly.
    """
    secret = os.environ.get('DEBUG_SECRET', None)
    header = request.META.get('HTTP_X_DEBUG_SECRET')
    if not secret or header != secret:
        return JsonResponse({'error': 'unauthorized'}, status=401)

    static_root = getattr(settings, 'STATIC_ROOT', None)
    react_static = os.path.join(str(getattr(settings, 'BASE_DIR', os.getcwd())), 'frontend', 'build', 'static')

    def list_files(root):
        files = []
        if root and os.path.exists(root):
            for dirpath, dirnames, filenames in os.walk(root):
                for f in filenames:
                    rel = os.path.relpath(os.path.join(dirpath, f), root)
                    files.append(rel)
        return files

    return JsonResponse({
        'static_root': static_root,
        'static_root_files': list_files(static_root),
        'react_static_dir': react_static,
        'react_static_files': list_files(react_static),
    })
    
