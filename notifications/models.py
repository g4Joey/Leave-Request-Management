from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    """
    Notification system for leave requests and approvals - supports requirement R5
    """
    NOTIFICATION_TYPES = [
        ('leave_submitted', 'Leave Request Submitted'),
        ('leave_manager_approved', 'Leave Request Approved by Manager'),
        ('leave_hr_approved', 'Leave Request Approved by HR'),
        ('leave_approved', 'Leave Request Fully Approved'),
        ('leave_rejected', 'Leave Request Rejected'),
        ('leave_cancelled', 'Leave Request Cancelled'),
        ('balance_low', 'Leave Balance Low'),
        ('system', 'System Notification'),
    ]
    
    # Recipients
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name='notifications')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                              null=True, blank=True, related_name='sent_notifications')
    
    # Notification content
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related objects
    leave_request = models.ForeignKey('leaves.LeaveRequest', on_delete=models.CASCADE,
                                     null=True, blank=True, related_name='notifications')
    
    # Status
    is_read = models.BooleanField(default=False)
    is_sent_email = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"{self.title} - {self.recipient.get_full_name()}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'


class EmailTemplate(models.Model):
    """
    Email templates for different notification types
    """
    notification_type = models.CharField(max_length=20, unique=True)
    subject_template = models.CharField(max_length=200)
    body_template = models.TextField()
    
    # Template variables help text
    available_variables = models.TextField(
        help_text="Available template variables (e.g., {employee_name}, {start_date}, {end_date})"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Email Template - {self.notification_type}"
    
    class Meta:
        ordering = ['notification_type']
        verbose_name = 'Email Template'
        verbose_name_plural = 'Email Templates'
