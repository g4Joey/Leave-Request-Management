from django.contrib.auth.models import AbstractUser
from django.db import models


class Affiliate(models.Model):
    """Company affiliate entity (e.g., Merban Capital, SDSL, SBL)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:  # pragma: no cover - simple
        return self.name


class Department(models.Model):
    """
    Department model for organizing users within the company
    """
    APPROVAL_FLOW_CHOICES = [
        ('hod_only', 'HOD Only'),
        ('hod_hr', 'HOD → HR'),
        ('hod_hr_ceo', 'HOD → HR → CEO'),
        ('hod_ceo', 'HOD → CEO'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional affiliate link (HR can manage departments under an affiliate)
    affiliate = models.ForeignKey(
        Affiliate, on_delete=models.CASCADE, null=True, blank=True, related_name='departments'
    )
    
    # Head of Department (HOD) / Manager for this department
    hod = models.ForeignKey(
        'CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='departments_headed'
    )
    
    # Approval flow configuration for this department
    approval_flow = models.CharField(
        max_length=20, 
        choices=APPROVAL_FLOW_CHOICES, 
        default='hod_hr',
        help_text='Defines the approval workflow for leave requests in this department'
    )
    
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
        ('junior_staff', 'Junior Staff'),
        ('senior_staff', 'Senior Staff'),
        ('manager', 'Manager'),
        ('hr', 'HR'),
        ('ceo', 'CEO'),
        ('admin', 'Admin'),
    ]
    
    # Basic profile information
    employee_id = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='junior_staff')
    department = models.ForeignKey(Department, on_delete=models.PROTECT, null=True, blank=True)
    affiliate = models.ForeignKey(Affiliate, on_delete=models.PROTECT, null=True, blank=True, 
                                 related_name='users')
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                               related_name='managed_employees')
    
    # Contact information
    phone = models.CharField(max_length=20, blank=True)
    
    # Employment details
    hire_date = models.DateField(null=True, blank=True)
    annual_leave_entitlement = models.PositiveIntegerField(default=25)  # days per year
    is_active_employee = models.BooleanField(default=True)

    # Flag for seeded demo accounts (added in migration 0003). These can be
    # hidden or treated specially in production analytics/views.
    is_demo = models.BooleanField(
        default=False,
        help_text='Designates a seeded demo account that may be hidden in production views.'
    )

    # Profile image
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)

    # Employment grade (Heads, Senior Officers, etc.)
    grade = models.ForeignKey(
        'EmploymentGrade', null=True, blank=True, on_delete=models.SET_NULL, related_name='users'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.employee_id})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_role_display_name(self):
        """Get the display name for the role (maps manager to HOD for UI)"""
        role_display_map = {
            'junior_staff': 'Junior Staff',
            'senior_staff': 'Senior Staff',
            'manager': 'HOD (Head of Department)',
            'hr': 'HR',
            'ceo': 'CEO',
            'admin': 'Admin',
        }
        return role_display_map.get(self.role, dict(self.ROLE_CHOICES).get(self.role, self.role))
    
    def is_hod(self):
        """Check if user is Head of Department for any department"""
        return self.departments_headed.exists()
    
    def get_headed_departments(self):
        """Get departments this user heads"""
        return self.departments_headed.all()
    
    def is_manager(self):
        """Check if user is a manager"""
        return self.role in ['manager', 'hr', 'admin']
    
    def is_hr(self):
        """Check if user is HR"""
        return self.role in ['hr', 'admin']
    
    def is_ceo(self):
        """Check if user is CEO"""
        return self.role in ['ceo', 'admin']
    
    def can_approve_leaves(self):
        """Check if user can approve leave requests"""
        return self.role in ['manager', 'hr', 'ceo', 'admin']

    # --- Data integrity enforcement ---
    def clean(self):  # type: ignore[override]
        from django.core.exceptions import ValidationError
        # Ensure affiliate is always present
        if not getattr(self, 'affiliate', None):
            # If department has an affiliate, adopt it
            if getattr(self, 'department', None) and getattr(self.department, 'affiliate', None):
                self.affiliate = self.department.affiliate
            else:
                raise ValidationError({'affiliate': 'Affiliate is required for all users.'})

        aff_name = (getattr(self.affiliate, 'name', '') or '').strip().upper()

        # SDSL/SBL: no departments or managers apply
        if aff_name in ['SDSL', 'SBL']:
            # Clear department/manager for non-admin users to avoid manager-stage routing
            if getattr(self, 'department', None) is not None:
                self.department = None
            if getattr(self, 'manager', None) is not None:
                self.manager = None

        # MERBAN: department required (except perhaps CEOs/admins)
        if aff_name in ['MERBAN', 'MERBAN CAPITAL']:
            # CEOs may not belong to a department; allow CEO/admin without department
            if self.role not in ['ceo', 'admin']:
                if not getattr(self, 'department', None):
                    raise ValidationError({'department': 'Department is required for Merban Capital users.'})
                # Department affiliate must match user affiliate
                dept_aff = getattr(getattr(self.department, 'affiliate', None), 'name', None)
                if (dept_aff or '').strip().upper() not in ['MERBAN', 'MERBAN CAPITAL']:
                    raise ValidationError({'department': 'Department must belong to Merban Capital.'})
    
    class Meta:
        ordering = ['employee_id']
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class EmploymentGrade(models.Model):
    """Employment grade representing rank/level for group entitlements."""
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # NOTE: After adding this model run migrations:
    #   python manage.py makemigrations users
    #   python manage.py migrate

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:  # pragma: no cover - simple
        return self.name
