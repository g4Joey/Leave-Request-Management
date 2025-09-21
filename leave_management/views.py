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
    and HTML for regular requests.
    """
    if request.path.startswith('/api/'):
        return JsonResponse({
            'error': 'Internal server error',
            'message': 'Something went wrong on our end. Please try again later.'
        }, status=500)
    
    # For non-API requests, you could render an HTML template
    from django.shortcuts import render
    return render(request, '500.html', status=500)

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

    