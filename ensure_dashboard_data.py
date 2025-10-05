"""
Simple script that runs on every app startup to ensure dashboard data exists.
This will be imported in settings_production.py to guarantee data is present.
"""
import logging

logger = logging.getLogger(__name__)

def ensure_dashboard_data():
    """Ensure leave balances exist for dashboard display"""
    try:
        from django.utils import timezone
        from leaves.models import LeaveBalance, LeaveType
        from users.models import CustomUser
        
        current_year = timezone.now().year
        
        # Get counts
        users_count = CustomUser.objects.filter(is_active=True, is_active_employee=True).count()
        leave_types_count = LeaveType.objects.filter(is_active=True).count()
        balances_count = LeaveBalance.objects.filter(year=current_year).count()
        
        logger.info(f"Dashboard data check: {users_count} users, {leave_types_count} leave types, {balances_count} balances")
        
        # If we have users and leave types but no balances, create them
        if users_count > 0 and leave_types_count > 0 and balances_count == 0:
            logger.info("Creating missing leave balances...")
            
            users = CustomUser.objects.filter(is_active=True, is_active_employee=True)
            leave_types = LeaveType.objects.filter(is_active=True)
            
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
                    
                    LeaveBalance.objects.get_or_create(
                        employee=user,
                        leave_type=leave_type,
                        year=current_year,
                        defaults={
                            'entitled_days': entitled_days,
                            'used_days': 0,
                            'pending_days': 0
                        }
                    )
                    created_count += 1
            
            logger.info(f"Created {created_count} leave balances for dashboard")
            
            # Create a sample leave request if none exist
            from leaves.models import LeaveRequest
            if not LeaveRequest.objects.filter(created_at__year=current_year).exists():
                sample_user = users.first()
                sample_leave_type = leave_types.first()
                
                if sample_user and sample_leave_type:
                    LeaveRequest.objects.create(
                        employee=sample_user,
                        leave_type=sample_leave_type,
                        start_date=timezone.now().date(),
                        end_date=timezone.now().date() + timezone.timedelta(days=1),
                        days_requested=2,
                        reason="Sample leave request",
                        status='pending'
                    )
                    logger.info("Created sample leave request")
        
        return True
        
    except Exception as e:
        logger.error(f"Error ensuring dashboard data: {e}")
        return False

# Run immediately when this module is imported
if __name__ != '__main__':
    try:
        # Small delay to ensure Django is fully initialized
        import time
        time.sleep(1)
        ensure_dashboard_data()
    except:
        pass  # Silently fail during import to avoid breaking app startup