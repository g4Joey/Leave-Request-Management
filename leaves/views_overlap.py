"""
Views for leave overlap detection API endpoints.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.conf import settings
from leaves.utils import find_overlaps, get_overlap_summary
import logging

logger = logging.getLogger('leaves')


class OverlapAPIView(APIView):
    """
    API endpoint for detecting leave overlaps within a department.
    
    GET /api/leaves/overlaps/?start=YYYY-MM-DD&end=YYYY-MM-DD&dept_id=NN&exclude_user_id=MM
    
    Query Parameters:
    - start (required): Start date in YYYY-MM-DD format
    - end (required): End date in YYYY-MM-DD format  
    - dept_id (required): Department ID to check overlaps within
    - exclude_user_id (optional): User ID to exclude from results
    
    Returns:
    - List of overlapping leave requests with minimal information
    - Privacy-conscious: only returns names, dates, and basic info
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Extract and validate query parameters
            start_date = request.query_params.get("start")
            end_date = request.query_params.get("end") 
            dept_id = request.query_params.get("dept_id")
            exclude_user_id = request.query_params.get("exclude_user_id")
            
            # Validate required parameters
            if not (start_date and end_date and dept_id):
                return Response(
                    {"detail": "start, end, and dept_id parameters are required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate department ID
            try:
                dept_id = int(dept_id)
            except (ValueError, TypeError):
                return Response(
                    {"detail": "dept_id must be a valid integer"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate exclude_user_id if provided
            if exclude_user_id is not None:
                try:
                    exclude_user_id = int(exclude_user_id)
                except (ValueError, TypeError):
                    return Response(
                        {"detail": "exclude_user_id must be a valid integer"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Check if overlap detection is enabled
            if not getattr(settings, 'OVERLAP_DETECT_ENABLED', True):
                return Response(
                    {"overlaps": [], "message": "Overlap detection is disabled"},
                    status=status.HTTP_200_OK
                )
            
            # Security check: ensure user can access this department's data
            user = request.user
            user_dept_id = getattr(user.department, 'id', None) if hasattr(user, 'department') else None
            
            # Allow access if user is from the same department, or is HR/Admin/CEO
            if (user_dept_id != dept_id and 
                not user.is_superuser and 
                getattr(user, 'role', '') not in ['hr', 'admin', 'ceo']):
                logger.warning(f"User {user.username} attempted to access overlap data for department {dept_id}")
                return Response(
                    {"detail": "Permission denied: Cannot access other department's data"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Find overlapping leave requests
            overlaps = find_overlaps(
                dept_id=dept_id,
                new_start=start_date,
                new_end=end_date,
                exclude_user_id=exclude_user_id
            )
            
            # Format response data
            overlap_data = []
            for overlap in overlaps:
                overlap_data.append({
                    "user_id": overlap.employee.id,
                    "name": overlap.employee.get_full_name(),
                    "start_date": str(overlap.start_date),
                    "end_date": str(overlap.end_date), 
                    "leave_type": overlap.leave_type.name,
                    "status": overlap.status,
                    "total_days": getattr(overlap, 'total_days', None)
                })
            
            logger.info(f"Overlap check for dept {dept_id}, dates {start_date}-{end_date}: {len(overlap_data)} overlaps found")
            
            return Response({
                "overlaps": overlap_data,
                "count": len(overlap_data),
                "department_id": dept_id,
                "date_range": f"{start_date} to {end_date}"
            })
            
        except Exception as e:
            logger.error(f"Error in overlap detection API: {str(e)}", exc_info=True)
            return Response(
                {"detail": "An error occurred while checking for overlaps"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OverlapSummaryAPIView(APIView):
    """
    Extended overlap API that includes summary statistics and overlap duration calculations.
    
    GET /api/leaves/overlaps/summary/?start=YYYY-MM-DD&end=YYYY-MM-DD&dept_id=NN&exclude_user_id=MM
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Extract and validate query parameters (same as OverlapAPIView)
            start_date = request.query_params.get("start")
            end_date = request.query_params.get("end")
            dept_id = request.query_params.get("dept_id")
            exclude_user_id = request.query_params.get("exclude_user_id")
            
            if not (start_date and end_date and dept_id):
                return Response(
                    {"detail": "start, end, and dept_id parameters are required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                dept_id = int(dept_id)
            except (ValueError, TypeError):
                return Response(
                    {"detail": "dept_id must be a valid integer"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            if exclude_user_id is not None:
                try:
                    exclude_user_id = int(exclude_user_id)
                except (ValueError, TypeError):
                    return Response(
                        {"detail": "exclude_user_id must be a valid integer"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Check permissions (same logic as OverlapAPIView)
            user = request.user
            user_dept_id = getattr(user.department, 'id', None) if hasattr(user, 'department') else None
            
            if (user_dept_id != dept_id and 
                not user.is_superuser and 
                getattr(user, 'role', '') not in ['hr', 'admin', 'ceo']):
                return Response(
                    {"detail": "Permission denied: Cannot access other department's data"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Find overlaps and generate summary
            overlaps = find_overlaps(
                dept_id=dept_id,
                new_start=start_date,
                new_end=end_date,
                exclude_user_id=exclude_user_id
            )
            
            from datetime import datetime
            new_start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            new_end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            overlap_summary = get_overlap_summary(overlaps, new_start_date, new_end_date)
            
            # Add notification threshold info
            from leaves.utils import should_trigger_overlap_notification, format_overlap_message
            
            should_notify = should_trigger_overlap_notification(overlap_summary)
            message = format_overlap_message(overlap_summary, "the requesting employee")
            
            return Response({
                "summary": overlap_summary,
                "should_notify": should_notify,
                "message": message,
                "thresholds": {
                    "min_days": getattr(settings, 'OVERLAP_NOTIFY_MIN_DAYS', 2),
                    "min_count": getattr(settings, 'OVERLAP_NOTIFY_MIN_COUNT', 2)
                },
                "department_id": dept_id,
                "date_range": f"{start_date} to {end_date}"
            })
            
        except Exception as e:
            logger.error(f"Error in overlap summary API: {str(e)}", exc_info=True)
            return Response(
                {"detail": "An error occurred while generating overlap summary"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )