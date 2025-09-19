from django.contrib.auth.models import AbstractUser
from django.db import models


class Department(models.Model):
    """
    Department model for organizing users
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class CustomUser(AbstractUser):
    """
    Extended User model to include leave management specific fields
    Supports requirements R4, R8, R10 for role-based access
    """
    ROLE_CHOICES = [
        ('staff', 'Staff'),
        ('manager', 'Manager'),
        ('hr', 'HR'),
        ('admin', 'Admin'),
    ]
    
    # Basic profile information
    employee_id = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    department = models.ForeignKey(Department, on_delete=models.PROTECT, null=True, blank=True)
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                               related_name='managed_employees')
    
    # Contact information
    phone = models.CharField(max_length=20, blank=True)
    
    # Employment details
    hire_date = models.DateField(null=True, blank=True)
    annual_leave_entitlement = models.PositiveIntegerField(default=25)  # days per year
    is_active_employee = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.employee_id})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def is_manager(self):
        """Check if user is a manager"""
        return self.role in ['manager', 'hr', 'admin']
    
    def is_hr(self):
        """Check if user is HR"""
        return self.role in ['hr', 'admin']
    
    def can_approve_leaves(self):
        """Check if user can approve leave requests"""
        return self.role in ['manager', 'hr', 'admin']
    
    class Meta:
        ordering = ['employee_id']
        verbose_name = 'User'
        verbose_name_plural = 'Users'
