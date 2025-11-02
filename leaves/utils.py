"""
Utility functions for leave request overlap detection and management.
"""

from django.db.models import Q
from datetime import date, datetime
from typing import List, Dict, Optional, Union
import logging

logger = logging.getLogger('leaves')


def find_overlaps(dept_id: int, new_start: Union[date, str], new_end: Union[date, str], 
                 exclude_user_id: Optional[int] = None, 
                 statuses: tuple = ('pending', 'manager_approved', 'hr_approved', 'approved')) -> 'QuerySet':
    """
    Find overlapping leave requests within a department.
    
    Inclusive overlap logic: start <= new_end and end >= new_start
    
    Args:
        dept_id: Department ID to search within
        new_start: Start date of the new leave (date object or YYYY-MM-DD string)
        new_end: End date of the new leave (date object or YYYY-MM-DD string)  
        exclude_user_id: Optional user ID to exclude from results
        statuses: Tuple of leave statuses to consider for overlaps
        
    Returns:
        QuerySet of LeaveRequest objects with related user data
    """
    from leaves.models import LeaveRequest
    
    # Convert string dates to date objects if needed
    if isinstance(new_start, str):
        new_start = datetime.strptime(new_start, '%Y-%m-%d').date()
    if isinstance(new_end, str):
        new_end = datetime.strptime(new_end, '%Y-%m-%d').date()
    
    # Base query filtering by department and status
    qs = LeaveRequest.objects.filter(
        employee__department_id=dept_id, 
        status__in=statuses
    )
    
    # Exclude specific user if provided
    if exclude_user_id:
        qs = qs.exclude(employee_id=exclude_user_id)
    
    # Apply overlap logic: existing leave overlaps if its start <= new_end and end >= new_start
    overlap_qs = qs.filter(
        start_date__lte=new_end,
        end_date__gte=new_start
    ).select_related('employee', 'leave_type')
    
    logger.debug(f"Found {overlap_qs.count()} overlapping leaves in department {dept_id} "
                f"for dates {new_start} to {new_end}")
    
    return overlap_qs


def calculate_overlap_duration(overlap_start: date, overlap_end: date, 
                             new_start: date, new_end: date) -> int:
    """
    Calculate the number of overlapping days between two date ranges.
    
    Args:
        overlap_start: Start date of existing leave
        overlap_end: End date of existing leave  
        new_start: Start date of new leave
        new_end: End date of new leave
        
    Returns:
        Number of overlapping days (inclusive)
    """
    # Find the actual overlap period
    actual_start = max(overlap_start, new_start)
    actual_end = min(overlap_end, new_end)
    
    # Calculate days (inclusive)
    if actual_start <= actual_end:
        overlap_days = (actual_end - actual_start).days + 1
    else:
        overlap_days = 0
        
    return overlap_days


def get_overlap_summary(overlaps: 'QuerySet', new_start: date, new_end: date) -> Dict:
    """
    Generate a summary of overlapping leaves with duration calculations.
    
    Args:
        overlaps: QuerySet of overlapping LeaveRequest objects
        new_start: Start date of new leave request  
        new_end: End date of new leave request
        
    Returns:
        Dictionary containing overlap statistics and details
    """
    overlap_details = []
    total_overlap_days = 0
    
    for overlap in overlaps:
        overlap_days = calculate_overlap_duration(
            overlap.start_date, overlap.end_date,
            new_start, new_end
        )
        
        if overlap_days > 0:
            total_overlap_days += overlap_days
            overlap_details.append({
                'user_id': overlap.employee_id,
                'name': overlap.employee.get_full_name(),
                'start_date': overlap.start_date,
                'end_date': overlap.end_date,
                'leave_type': overlap.leave_type.name,
                'status': overlap.status,
                'overlap_days': overlap_days
            })
    
    return {
        'total_overlaps': len(overlap_details),
        'total_overlap_days': total_overlap_days,
        'overlaps': overlap_details
    }


def should_trigger_overlap_notification(overlap_summary: Dict) -> bool:
    """
    Determine if an overlap should trigger notifications based on configured thresholds.
    
    Args:
        overlap_summary: Dictionary returned by get_overlap_summary()
        
    Returns:
        Boolean indicating if notification should be sent
    """
    from django.conf import settings
    
    min_days = getattr(settings, 'OVERLAP_NOTIFY_MIN_DAYS', 2)
    min_count = getattr(settings, 'OVERLAP_NOTIFY_MIN_COUNT', 2)
    enabled = getattr(settings, 'OVERLAP_DETECT_ENABLED', True)
    
    if not enabled:
        return False
    
    # Check if we have enough overlaps and overlap duration
    significant_overlaps = [
        overlap for overlap in overlap_summary['overlaps'] 
        if overlap['overlap_days'] >= min_days
    ]
    
    return len(significant_overlaps) >= min_count


def format_overlap_message(overlap_summary: Dict, employee_name: str) -> str:
    """
    Format a user-friendly message about leave overlaps.
    
    Args:
        overlap_summary: Dictionary returned by get_overlap_summary()
        employee_name: Name of employee submitting the request
        
    Returns:
        Formatted message string
    """
    total_overlaps = overlap_summary['total_overlaps']
    
    if total_overlaps == 0:
        return "No overlapping leaves detected."
    
    overlap_names = [overlap['name'] for overlap in overlap_summary['overlaps']]
    
    if total_overlaps == 1:
        return f"This request overlaps with {overlap_names[0]}'s leave."
    elif total_overlaps <= 3:
        names_str = ', '.join(overlap_names[:-1]) + f" and {overlap_names[-1]}"
        return f"This request overlaps with leaves from {names_str}."
    else:
        first_two = ', '.join(overlap_names[:2])
        remaining = total_overlaps - 2
        return f"This request overlaps with leaves from {first_two} and {remaining} others."


def get_overlap_privacy_data(overlap_summary: Dict) -> List[Dict]:
    """
    Return privacy-safe overlap data for notifications (names and dates only).
    
    Args:
        overlap_summary: Dictionary returned by get_overlap_summary()
        
    Returns:
        List of dictionaries with minimal overlap information
    """
    return [
        {
            'name': overlap['name'],
            'start_date': str(overlap['start_date']),
            'end_date': str(overlap['end_date']),
            'overlap_days': overlap['overlap_days']
        }
        for overlap in overlap_summary['overlaps']
    ]