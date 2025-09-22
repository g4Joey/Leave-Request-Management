from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta


class LeaveType(models.Model):
    """
    Different types of leave (Annual, Sick, Maternity, etc.)
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    max_days_per_request = models.PositiveIntegerField(default=30)
    requires_medical_certificate = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class LeaveRequest(models.Model):
    """
    Core leave request model - supports requirements R1, R2, R4, R5, R12
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Request details
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                                related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    
    # Leave dates
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.PositiveIntegerField()
    
    # Request information
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Approval workflow
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='approved_leaves')
    approval_date = models.DateTimeField(null=True, blank=True)
    approval_comments = models.TextField(blank=True)
    
    # Attachments
    medical_certificate = models.FileField(upload_to='medical_certificates/', 
                                         null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def clean(self):
        """Validate leave request data"""
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValidationError("Start date cannot be after end date")
            
            # Only enforce future-dated constraint while request is pending
            if self.status == 'pending' and self.start_date < timezone.now().date():
                raise ValidationError("Cannot request leave for past dates while pending")
    
    def save(self, *args, **kwargs):
        # Calculate total days if not provided
        if self.start_date and self.end_date and not self.total_days:
            self.total_days = self.calculate_working_days()
        
        self.clean()
        super().save(*args, **kwargs)
    
    def calculate_working_days(self):
        """Calculate working days between start and end date (excluding weekends)"""
        if not self.start_date or not self.end_date:
            return 0
        
        current_date = self.start_date
        working_days = 0
        
        while current_date <= self.end_date:
            # Count only weekdays (Monday=0, Sunday=6)
            if current_date.weekday() < 5:  # Monday to Friday
                working_days += 1
            current_date += timedelta(days=1)
        
        return working_days
    
    def approve(self, approved_by, comments=""):
        """Approve the leave request"""
        self.status = 'approved'
        self.approved_by = approved_by
        self.approval_date = timezone.now()
        self.approval_comments = comments
        self.save()
    
    def reject(self, rejected_by, comments=""):
        """Reject the leave request"""
        self.status = 'rejected'
        self.approved_by = rejected_by
        self.approval_date = timezone.now()
        self.approval_comments = comments
        self.save()
    
    @property
    def is_pending(self):
        return self.status == 'pending'
    
    @property
    def is_approved(self):
        return self.status == 'approved'
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.leave_type.name} ({self.start_date} to {self.end_date})"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Leave Request'
        verbose_name_plural = 'Leave Requests'


class LeaveBalance(models.Model):
    """
    Track leave balances for each employee - supports requirements R2, R3
    """
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.PositiveIntegerField(default=timezone.now().year)
    
    # Balance tracking
    entitled_days = models.PositiveIntegerField(default=0)
    used_days = models.PositiveIntegerField(default=0)
    pending_days = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def remaining_days(self):
        """Calculate remaining leave days"""
        return max(0, self.entitled_days - self.used_days - self.pending_days)
    
    def update_balance(self):
        """Update used and pending days based on current leave requests"""
        current_year_requests = LeaveRequest.objects.filter(
            employee=self.employee,
            leave_type=self.leave_type,
            start_date__year=self.year
        )
        
        # Calculate used days (approved leaves)
        self.used_days = sum(
            req.total_days for req in current_year_requests.filter(status='approved')
        )
        
        # Calculate pending days
        self.pending_days = sum(
            req.total_days for req in current_year_requests.filter(status='pending')
        )
        
        self.save()
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.leave_type.name} {self.year} ({self.remaining_days} days remaining)"
    
    class Meta:
        unique_together = ['employee', 'leave_type', 'year']
        ordering = ['employee', 'leave_type', 'year']
        verbose_name = 'Leave Balance'
        verbose_name_plural = 'Leave Balances'


class LeavePolicy(models.Model):
    """
    Leave policies and rules - supports requirement R7
    """
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    department = models.ForeignKey('users.Department', on_delete=models.CASCADE, 
                                  null=True, blank=True)
    
    # Policy rules
    max_consecutive_days = models.PositiveIntegerField(default=30)
    min_advance_notice_days = models.PositiveIntegerField(default=1)
    carry_forward_allowed = models.BooleanField(default=False)
    max_carry_forward_days = models.PositiveIntegerField(default=0)
    
    # Blackout periods (simple text for now)
    blackout_periods = models.TextField(blank=True, 
                                       help_text="Periods when leave is not allowed (e.g., Dec 24-31)")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        dept_name = self.department.name if self.department else "All Departments"
        return f"{self.leave_type.name} Policy - {dept_name}"
    
    class Meta:
        ordering = ['leave_type', 'department']
        verbose_name = 'Leave Policy'
        verbose_name_plural = 'Leave Policies'
