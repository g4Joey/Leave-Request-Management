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
        ('pending', 'Pending Manager Approval'),
        ('manager_approved', 'Manager Approved - Pending HR'),
        ('hr_approved', 'HR Approved - Pending CEO'),
        ('approved', 'Fully Approved'),
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
    total_days = models.PositiveIntegerField(blank=True, null=True)
    
    # Request information (reason now optional for staff)
    reason = models.TextField(blank=True, null=True, help_text="Optional reason provided by employee")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Multi-stage approval workflow
    # Manager approval
    manager_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                           null=True, blank=True, related_name='manager_approved_leaves')
    manager_approval_date = models.DateTimeField(null=True, blank=True)
    manager_approval_comments = models.TextField(blank=True)
    
    # HR approval
    hr_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                      null=True, blank=True, related_name='hr_approved_leaves')
    hr_approval_date = models.DateTimeField(null=True, blank=True)
    hr_approval_comments = models.TextField(blank=True)
    
    # CEO approval
    ceo_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                       null=True, blank=True, related_name='ceo_approved_leaves')
    ceo_approval_date = models.DateTimeField(null=True, blank=True)
    ceo_approval_comments = models.TextField(blank=True)
    
    # Final approval (legacy field - will point to CEO)
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
        # Always calculate total days from dates
        if self.start_date and self.end_date:
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

    @property
    def working_days(self):  # explicit alias for clarity in serializers/UI
        return self.total_days

    @property
    def calendar_days(self):
        if not self.start_date or not self.end_date:
            return 0
        return (self.end_date - self.start_date).days + 1

    @property
    def range_with_days(self):
        """Human friendly range summary including working days (used by UI)."""
        if not self.start_date or not self.end_date:
            return "(dates pending)"
        wd = self.working_days or self.calculate_working_days()
        label = "working day" if wd == 1 else "working days"
        return f"{self.start_date} to {self.end_date} ({wd} {label})"
    
    def manager_approve(self, approved_by, comments=""):
        """Manager approves the leave request"""
        self.status = 'manager_approved'
        self.manager_approved_by = approved_by
        self.manager_approval_date = timezone.now()
        self.manager_approval_comments = comments
        self.save()
    
    def hr_approve(self, approved_by, comments=""):
        """HR approves the leave request"""
        self.status = 'hr_approved'
        self.hr_approved_by = approved_by
        self.hr_approval_date = timezone.now()
        self.hr_approval_comments = comments
        self.save()
    
    def ceo_approve(self, approved_by, comments=""):
        """CEO gives final approval"""
        self.status = 'approved'
        self.ceo_approved_by = approved_by
        self.ceo_approval_date = timezone.now()
        self.ceo_approval_comments = comments
        # Set legacy fields for backward compatibility
        self.approved_by = approved_by
        self.approval_date = self.ceo_approval_date
        self.approval_comments = comments
        self.save()
    
    def reject(self, rejected_by, comments="", rejection_stage=""):
        """Reject the leave request at any stage"""
        self.status = 'rejected'
        # Record who rejected it based on their role
        if hasattr(rejected_by, 'role'):
            if rejected_by.role == 'manager':
                self.manager_approved_by = rejected_by
                self.manager_approval_date = timezone.now()
                self.manager_approval_comments = f"REJECTED: {comments}"
            elif rejected_by.role == 'hr':
                self.hr_approved_by = rejected_by
                self.hr_approval_date = timezone.now()
                self.hr_approval_comments = f"REJECTED: {comments}"
            elif rejected_by.role in ['ceo', 'admin']:
                self.ceo_approved_by = rejected_by
                self.ceo_approval_date = timezone.now()
                self.ceo_approval_comments = f"REJECTED: {comments}"
        
        # Set legacy fields
        self.approved_by = rejected_by
        self.approval_date = timezone.now()
        self.approval_comments = f"REJECTED: {comments}"
        self.save()
    
    def approve(self, approved_by, comments=""):
        """Legacy approve method - redirects to appropriate approval stage"""
        if hasattr(approved_by, 'role'):
            if approved_by.role == 'manager' and self.status == 'pending':
                self.manager_approve(approved_by, comments)
            elif approved_by.role == 'hr' and self.status == 'manager_approved':
                self.hr_approve(approved_by, comments)
            elif approved_by.role in ['ceo', 'admin'] and self.status == 'hr_approved':
                self.ceo_approve(approved_by, comments)
            else:
                # For backward compatibility or admin override
                self.status = 'approved'
                self.approved_by = approved_by
                self.approval_date = timezone.now()
                self.approval_comments = comments
                self.save()
        else:
            # Fallback to old behavior
            self.status = 'approved'
            self.approved_by = approved_by
            self.approval_date = timezone.now()
            self.approval_comments = comments
            self.save()
    
    @property
    def is_pending(self):
        return self.status == 'pending'
    
    @property
    def is_manager_approved(self):
        return self.status == 'manager_approved'
    
    @property
    def is_hr_approved(self):
        return self.status == 'hr_approved'
    
    @property
    def is_approved(self):
        return self.status == 'approved'
    
    @property
    def is_rejected(self):
        return self.status == 'rejected'
    
    @property
    def current_approval_stage(self):
        """Return which stage of approval this request is at"""
        if self.status == 'pending':
            return 'manager'
        elif self.status == 'manager_approved':
            return 'hr'
        elif self.status == 'hr_approved':
            return 'ceo'
        elif self.status == 'approved':
            return 'completed'
        elif self.status == 'rejected':
            return 'rejected'
        else:
            return 'unknown'
    
    @property
    def next_approver_role(self):
        """Return the role of the next person who needs to approve"""
        stage = self.current_approval_stage
        if stage == 'manager':
            return 'manager'
        elif stage == 'hr':
            return 'hr'
        elif stage == 'ceo':
            return 'ceo'
        else:
            return None
    
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
            req.total_days or 0 for req in current_year_requests.filter(status='approved')
        )
        
        # Calculate pending days (all requests in approval workflow)
        pending_statuses = ['pending', 'manager_approved', 'hr_approved']
        self.pending_days = sum(
            req.total_days or 0 for req in current_year_requests.filter(status__in=pending_statuses)
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


class LeaveGradeEntitlement(models.Model):
    """Entitlement per leave type for a specific employment grade."""
    grade = models.ForeignKey('users.EmploymentGrade', on_delete=models.CASCADE, related_name='entitlements')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='grade_entitlements')
    entitled_days = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # NOTE: After adding this model run migrations:
    #   python manage.py makemigrations leaves
    #   python manage.py migrate

    class Meta:
        unique_together = ('grade', 'leave_type')
        ordering = ['grade__name', 'leave_type__name']
        verbose_name = 'Grade Entitlement'
        verbose_name_plural = 'Grade Entitlements'

    def __str__(self):  # pragma: no cover
        return f"{self.grade.name} - {self.leave_type.name}: {self.entitled_days}"
