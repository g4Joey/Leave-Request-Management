from rest_framework import serializers
from django.utils import timezone
from django.db.models import Q
from .models import LeaveRequest, LeaveType, LeaveBalance, LeaveGradeEntitlement
from users.models import EmploymentGrade
from django.contrib.auth import get_user_model

User = get_user_model()


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        # Use correct model fields
        fields = ['id', 'name', 'description', 'max_days_per_request', 'requires_medical_certificate', 'is_active']


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    remaining_days = serializers.SerializerMethodField()
    
    class Meta:
        model = LeaveBalance
        fields = ['id', 'leave_type', 'leave_type_name', 'entitled_days', 
                 'used_days', 'pending_days', 'remaining_days', 'year']
        read_only_fields = ['used_days', 'pending_days']
    
    def get_remaining_days(self, obj):
        return obj.entitled_days - obj.used_days - obj.pending_days


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_email = serializers.CharField(source='employee.email', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    total_days = serializers.IntegerField(read_only=True, help_text="Working days (weekdays) between start and end date")
    working_days = serializers.IntegerField(read_only=True)
    calendar_days = serializers.IntegerField(read_only=True)
    range_with_days = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'employee', 'employee_name', 'employee_email',
            'leave_type', 'leave_type_name', 'start_date', 'end_date',
            'total_days', 'working_days', 'calendar_days', 'range_with_days', 'reason', 'status', 'status_display',
            'approved_by', 'approved_by_name', 'approval_comments',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['employee', 'status', 'approved_by', 'approval_comments', 
                           'created_at', 'updated_at']
        extra_kwargs = {
            'reason': {'required': False, 'allow_blank': True}
        }
    
    # total_days is computed in model.save() (working days). Expose as read-only.
    
    def validate(self, attrs):
        """
        Validate leave request data according to business rules
        """
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        leave_type = attrs.get('leave_type')
        
        # Basic date validation
        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError("Start date cannot be after end date.")
            
            # Allow next year requests: Allow current year and next year only
            current_date = timezone.now().date()
            max_allowed_year = current_date.year + 1
            
            if start_date < current_date:
                raise serializers.ValidationError("Cannot submit leave request for past dates.")
            
            if start_date.year > max_allowed_year:
                raise serializers.ValidationError(f"Cannot submit leave request beyond {max_allowed_year}.")
            
            # Working days (weekdays only) to enforce balance realistically
            total_days = self._calculate_working_days(start_date, end_date)
            
            # Check leave balance
            if leave_type and hasattr(self.context.get('request'), 'user'):
                user = self.context['request'].user
                try:
                    balance = LeaveBalance.objects.get(
                        employee=user,
                        leave_type=leave_type,
                        year=start_date.year
                    )
                    
                    # Check if user has enough balance
                    remaining_days = balance.entitled_days - balance.used_days - balance.pending_days
                    if total_days > remaining_days:
                        raise serializers.ValidationError(
                            f"Insufficient leave balance. You have {remaining_days} days remaining."
                        )
                        
                except LeaveBalance.DoesNotExist:
                    # Auto-create next year balance if needed
                    if start_date.year == timezone.now().date().year + 1:
                        balance = self._create_next_year_balance(user, leave_type, start_date.year)
                        # Check if user has enough balance
                        remaining_days = balance.entitled_days - balance.used_days - balance.pending_days
                        if total_days > remaining_days:
                            raise serializers.ValidationError(
                                f"Insufficient leave balance. You have {remaining_days} days remaining."
                            )
                    else:
                        raise serializers.ValidationError(
                            f"No leave balance found for {leave_type.name} in {start_date.year}."
                        )
            
            # Check for overlapping leave requests
            if hasattr(self.context.get('request'), 'user'):
                user = self.context['request'].user
                overlapping_requests = LeaveRequest.objects.filter(
                    employee=user,
                    status__in=['pending', 'approved'],
                    start_date__lte=end_date,
                    end_date__gte=start_date
                )
                
                # Exclude current instance if updating
                if self.instance:
                    overlapping_requests = overlapping_requests.exclude(id=self.instance.id)
                
                if overlapping_requests.exists():
                    raise serializers.ValidationError(
                        "You have overlapping leave requests for the selected dates."
                    )
        
        return attrs
    
    def create(self, validated_data):
        # Set the employee to the current user
        validated_data['employee'] = self.context['request'].user
        return super().create(validated_data)

    # Reuse same working-day logic the model uses (avoid import cycle / duplication risk if moved later)
    def _calculate_working_days(self, start, end):
        from datetime import timedelta
        current = start
        wd = 0
        while current <= end:
            if current.weekday() < 5:
                wd += 1
            current += timedelta(days=1)
        return wd
    
    def _create_next_year_balance(self, user, leave_type, year):
        """Auto-create next year leave balance using current year entitlements as baseline"""
        from .models import LeaveBalance
        
        # Try to get current year balance as reference for entitlements
        current_year = timezone.now().year
        try:
            current_balance = LeaveBalance.objects.get(
                employee=user,
                leave_type=leave_type,
                year=current_year
            )
            entitled_days = current_balance.entitled_days
        except LeaveBalance.DoesNotExist:
            # Fallback to default entitlements
            entitled_days = self._get_default_entitlement(user, leave_type)
        
        # Create next year balance
        balance = LeaveBalance.objects.create(
            employee=user,
            leave_type=leave_type,
            year=year,
            entitled_days=entitled_days,
            used_days=0,
            pending_days=0
        )
        return balance
    
    def _get_default_entitlement(self, user, leave_type):
        """Get default entitlement based on leave type and user role"""
        type_name = leave_type.name.lower()
        
        if 'annual' in type_name:
            return getattr(user, 'annual_leave_entitlement', 25)
        elif 'sick' in type_name:
            return 14 if user.role in ['manager', 'admin', 'hr'] else 10
        elif 'maternity' in type_name:
            return 90 if user.role in ['manager', 'admin', 'hr'] else 84
        elif 'paternity' in type_name:
            return 14 if user.role in ['manager', 'admin', 'hr'] else 7
        elif 'compassionate' in type_name:
            return 5
        elif 'casual' in type_name:
            return 7 if user.role in ['manager', 'admin', 'hr'] else 5
        else:
            return 10


class LeaveRequestListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views"""
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_email = serializers.CharField(source='employee.email', read_only=True)
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    employee_role = serializers.CharField(source='employee.role', read_only=True)
    employee_department = serializers.CharField(source='employee.department.name', read_only=True)
    employee_department_affiliate = serializers.SerializerMethodField()
    employee_department_id = serializers.SerializerMethodField()
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    # DRF will raise an AssertionError if `source` is identical to the field name.
    # Keep this as a plain read-only CharField to avoid redundant `source=` usage.
    manager_approval_comments = serializers.CharField(read_only=True)
    total_days = serializers.IntegerField(read_only=True, help_text="Working days (weekdays)")
    working_days = serializers.IntegerField(read_only=True)
    calendar_days = serializers.IntegerField(read_only=True)
    range_with_days = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    manager_comments = serializers.CharField(read_only=True)
    hr_comments = serializers.CharField(read_only=True)
    ceo_approval_date = serializers.DateTimeField(read_only=True)
    manager_approval_date = serializers.DateTimeField(read_only=True)
    hr_approval_date = serializers.DateTimeField(read_only=True)
    stage_label = serializers.SerializerMethodField()
    
    def get_employee_department_affiliate(self, obj):
        """Get the affiliate name for the employee's department"""
        try:
            # Prefer department's affiliate
            if getattr(obj, 'employee', None) and getattr(obj.employee, 'department', None):
                dept = obj.employee.department
                if getattr(dept, 'affiliate', None) and getattr(dept.affiliate, 'name', None):
                    return dept.affiliate.name
            # Fallback to user's affiliate
            if getattr(obj, 'employee', None) and getattr(obj.employee, 'affiliate', None):
                if getattr(obj.employee.affiliate, 'name', None):
                    return obj.employee.affiliate.name
        except Exception:
            pass
        return 'Other'

    def get_employee_department_id(self, obj):
        try:
            if getattr(obj, 'employee', None) and getattr(obj.employee, 'department', None):
                return obj.employee.department.id
        except Exception:
            return None
        return None

    def _get_affiliate_name(self, obj):
        emp = getattr(obj, 'employee', None)
        if not emp:
            return None
        # Prefer department affiliate, then user affiliate
        try:
            if getattr(emp, 'department', None) and getattr(emp.department, 'affiliate', None):
                return emp.department.affiliate.name
        except Exception:
            pass
        try:
            if getattr(emp, 'affiliate', None):
                return emp.affiliate.name
        except Exception:
            pass
        return None

    def get_stage_label(self, obj):
        """Human-friendly label pointing to the next required approval step.
        Examples: 'Pending HR approval', 'Pending CEO approval'."""
        status = getattr(obj, 'status', None)
        aff = (self._get_affiliate_name(obj) or '').upper()
        def aff_ceo_label(a: str) -> str:
            if a == 'SDSL':
                return 'Pending SDSL CEO Approval'
            if a == 'SBL':
                return 'Pending SBL CEO Approval'
            if a in ['MERBAN', 'MERBAN CAPITAL']:
                return 'Pending Merban CEO Approval'
            return 'Pending CEO Approval'
        if status == 'manager_approved':
            # SDSL/SBL flow: CEO comes before HR. Standard (Merban): HR next.
            if aff in ['SDSL', 'SBL']:
                return aff_ceo_label(aff)
            return 'Pending HR approval'
        if status == 'hr_approved':
            # After HR, next is CEO in standard; in SDSL, HR_approved means CEO already acted and HR will finalize next
            if aff in ['SDSL', 'SBL']:
                return 'Pending HR final approval'
            return aff_ceo_label(aff)
        if status == 'ceo_approved':
            return 'Pending HR approval'
        if status == 'pending':
            # For SDSL/SBL there is no manager step; CEO is first approver
            if aff in ['SDSL', 'SBL']:
                return aff_ceo_label(aff)
            return 'Pending Manager approval'
        if status == 'approved':
            return 'Approved'
        if status == 'rejected':
            return 'Rejected'
        if status == 'cancelled':
            return 'Cancelled'
        return getattr(obj, 'get_status_display', lambda: status)()
    
    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'employee_name', 'employee_email', 'employee_id', 'employee_role', 
            'employee_department', 'employee_department_id', 'employee_department_affiliate', 'leave_type_name', 
            'start_date', 'end_date', 'total_days', 'working_days', 'calendar_days', 'range_with_days',
            'status', 'status_display', 'stage_label', 'reason', 'manager_approval_comments', 'manager_comments', 'hr_comments', 
            'manager_approval_date', 'hr_approval_date', 'ceo_approval_date', 'created_at'
        ]
    
    # total_days is computed in model.save() (working days). Expose as read-only.


class LeaveApprovalSerializer(serializers.ModelSerializer):
    """Serializer for manager approval/rejection actions"""
    
    class Meta:
        model = LeaveRequest
        fields = ['status', 'approval_comments']
    
    def validate_status(self, value):
        if value not in ['approved', 'rejected']:
            raise serializers.ValidationError("Status must be either approved or rejected.")
        return value
    
    def update(self, instance, validated_data):
        # Set the approved_by to the current user
        validated_data['approved_by'] = self.context['request'].user
        
        # Update the instance fields manually
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Stamp the approval date/time when status changes
        from django.utils import timezone
        instance.approval_date = timezone.now()
        
        # Save the instance
        instance.save()
        return instance


class EmploymentGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmploymentGrade
        fields = ['id', 'name', 'slug', 'description', 'is_active']


class LeaveGradeEntitlementSerializer(serializers.ModelSerializer):
    grade = EmploymentGradeSerializer(read_only=True)
    grade_id = serializers.PrimaryKeyRelatedField(source='grade', queryset=EmploymentGrade.objects.filter(is_active=True), write_only=True)
    leave_type = serializers.StringRelatedField(read_only=True)
    leave_type_id = serializers.PrimaryKeyRelatedField(source='leave_type', queryset=LeaveType.objects.filter(is_active=True))

    class Meta:
        model = LeaveGradeEntitlement
        fields = ['id', 'grade', 'grade_id', 'leave_type', 'leave_type_id', 'entitled_days']