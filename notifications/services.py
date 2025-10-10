from django.contrib.auth import get_user_model
from .models import Notification
import logging

User = get_user_model()
logger = logging.getLogger('notifications')


class LeaveNotificationService:
    """Service to handle leave request notifications across the approval workflow"""
    
    @staticmethod
    def notify_leave_submitted(leave_request):
        """Notify manager when leave is submitted"""
        try:
            # Notify the employee's manager
            if leave_request.employee.manager:
                Notification.objects.create(
                    recipient=leave_request.employee.manager,
                    sender=leave_request.employee,
                    notification_type='leave_submitted',
                    title=f'New Leave Request from {leave_request.employee.get_full_name()}',
                    message=f'{leave_request.employee.get_full_name()} has submitted a leave request for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date}.',
                    leave_request=leave_request
                )
                logger.info(f'Notified manager {leave_request.employee.manager.username} of new leave request {leave_request.id}')
            else:
                # If no manager assigned, notify HR directly
                hr_users = User.objects.filter(role='hr', is_active=True)
                for hr_user in hr_users:
                    Notification.objects.create(
                        recipient=hr_user,
                        sender=leave_request.employee,
                        notification_type='leave_submitted',
                        title=f'New Leave Request (No Manager Assigned)',
                        message=f'{leave_request.employee.get_full_name()} has submitted a leave request for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date}. No manager assigned.',
                        leave_request=leave_request
                    )
                logger.info(f'No manager assigned for {leave_request.employee.username}, notified HR of leave request {leave_request.id}')
        except Exception as e:
            logger.error(f'Error sending leave submission notification: {str(e)}', exc_info=True)
    
    @staticmethod
    def notify_manager_approval(leave_request, approved_by):
        """Notify relevant parties when manager approves"""
        try:
            # Notify employee
            Notification.objects.create(
                recipient=leave_request.employee,
                sender=approved_by,
                notification_type='leave_manager_approved',
                title='Leave Request Approved by Manager',
                message=f'Your leave request for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date} has been approved by your manager and forwarded to HR for final review.',
                leave_request=leave_request
            )
            
            # Notify all HR users
            hr_users = User.objects.filter(role='hr', is_active=True)
            for hr_user in hr_users:
                Notification.objects.create(
                    recipient=hr_user,
                    sender=approved_by,
                    notification_type='leave_manager_approved',
                    title=f'Leave Request Ready for HR Review',
                    message=f'A leave request from {leave_request.employee.get_full_name()} for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date} has been approved by the manager and requires HR review.',
                    leave_request=leave_request
                )
            
            logger.info(f'Notified employee and HR of manager approval for leave request {leave_request.id}')
        except Exception as e:
            logger.error(f'Error sending manager approval notification: {str(e)}', exc_info=True)
    
    @staticmethod
    def notify_hr_approval(leave_request, approved_by):
        """Notify relevant parties when HR approves"""
        try:
            # Notify employee
            Notification.objects.create(
                recipient=leave_request.employee,
                sender=approved_by,
                notification_type='leave_hr_approved',
                title='Leave Request Approved by HR',
                message=f'Your leave request for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date} has been approved by HR and forwarded to CEO for final approval.',
                leave_request=leave_request
            )
            
            # Notify manager
            if leave_request.employee.manager:
                Notification.objects.create(
                    recipient=leave_request.employee.manager,
                    sender=approved_by,
                    notification_type='leave_hr_approved',
                    title='Leave Request Approved by HR',
                    message=f'The leave request from {leave_request.employee.get_full_name()} for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date} has been approved by HR and forwarded to CEO.',
                    leave_request=leave_request
                )
            
            # Notify CEO
            ceo_users = User.objects.filter(role='ceo', is_active=True)
            for ceo_user in ceo_users:
                Notification.objects.create(
                    recipient=ceo_user,
                    sender=approved_by,
                    notification_type='leave_hr_approved',
                    title=f'Leave Request Ready for CEO Approval',
                    message=f'A leave request from {leave_request.employee.get_full_name()} for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date} has been approved by HR and requires CEO approval.',
                    leave_request=leave_request
                )
            
            logger.info(f'Notified employee, manager, and CEO of HR approval for leave request {leave_request.id}')
        except Exception as e:
            logger.error(f'Error sending HR approval notification: {str(e)}', exc_info=True)
    
    @staticmethod
    def notify_ceo_approval(leave_request, approved_by):
        """Notify relevant parties when CEO gives final approval"""
        try:
            # Notify employee
            Notification.objects.create(
                recipient=leave_request.employee,
                sender=approved_by,
                notification_type='leave_approved',
                title='Leave Request FULLY APPROVED',
                message=f'Congratulations! Your leave request for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date} has received final approval from the CEO.',
                leave_request=leave_request
            )
            
            # Notify manager
            if leave_request.employee.manager:
                Notification.objects.create(
                    recipient=leave_request.employee.manager,
                    sender=approved_by,
                    notification_type='leave_approved',
                    title='Leave Request Fully Approved',
                    message=f'The leave request from {leave_request.employee.get_full_name()} for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date} has received final approval from the CEO.',
                    leave_request=leave_request
                )
            
            # Notify HR
            hr_users = User.objects.filter(role='hr', is_active=True)
            for hr_user in hr_users:
                Notification.objects.create(
                    recipient=hr_user,
                    sender=approved_by,
                    notification_type='leave_approved',
                    title='Leave Request Fully Approved',
                    message=f'The leave request from {leave_request.employee.get_full_name()} for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date} has received final approval from the CEO.',
                    leave_request=leave_request
                )
            
            logger.info(f'Notified all parties of CEO approval for leave request {leave_request.id}')
        except Exception as e:
            logger.error(f'Error sending CEO approval notification: {str(e)}', exc_info=True)
    
    @staticmethod
    def notify_rejection(leave_request, rejected_by, rejection_stage):
        """Notify relevant parties when leave is rejected at any stage"""
        try:
            stage_name = {
                'manager': 'Manager',
                'hr': 'HR',
                'ceo': 'CEO'
            }.get(rejection_stage, 'Unknown')
            
            # Always notify the employee
            Notification.objects.create(
                recipient=leave_request.employee,
                sender=rejected_by,
                notification_type='leave_rejected',
                title=f'Leave Request Rejected by {stage_name}',
                message=f'Your leave request for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date} has been rejected by {stage_name}. Reason: {leave_request.approval_comments}',
                leave_request=leave_request
            )
            
            # Manager rejection - employee already notified above
            # No additional notifications needed since manager is the first stage
            
            # If rejected by HR, notify manager
            if rejection_stage == 'hr' and leave_request.employee.manager:
                Notification.objects.create(
                    recipient=leave_request.employee.manager,
                    sender=rejected_by,
                    notification_type='leave_rejected',
                    title='Leave Request Rejected by HR',
                    message=f'The leave request from {leave_request.employee.get_full_name()} for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date} has been rejected by HR. Reason: {leave_request.approval_comments}',
                    leave_request=leave_request
                )
            
            # If rejected by CEO, notify both manager and HR
            elif rejection_stage == 'ceo':
                if leave_request.employee.manager:
                    Notification.objects.create(
                        recipient=leave_request.employee.manager,
                        sender=rejected_by,
                        notification_type='leave_rejected',
                        title='Leave Request Rejected by CEO',
                        message=f'The leave request from {leave_request.employee.get_full_name()} for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date} has been rejected by the CEO. Reason: {leave_request.approval_comments}',
                        leave_request=leave_request
                    )
                
                hr_users = User.objects.filter(role='hr', is_active=True)
                for hr_user in hr_users:
                    Notification.objects.create(
                        recipient=hr_user,
                        sender=rejected_by,
                        notification_type='leave_rejected',
                        title='Leave Request Rejected by CEO',
                        message=f'The leave request from {leave_request.employee.get_full_name()} for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date} has been rejected by the CEO. Reason: {leave_request.approval_comments}',
                        leave_request=leave_request
                    )
            
            logger.info(f'Notified relevant parties of rejection at {stage_name} level for leave request {leave_request.id}')
        except Exception as e:
            logger.error(f'Error sending rejection notification: {str(e)}', exc_info=True)