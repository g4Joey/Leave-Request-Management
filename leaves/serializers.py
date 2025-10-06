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
            
            if start_date < timezone.now().date():
                raise serializers.ValidationError("Cannot submit leave request for past dates.")
            
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


class LeaveRequestListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views"""
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    total_days = serializers.IntegerField(read_only=True, help_text="Working days (weekdays)")
    working_days = serializers.IntegerField(read_only=True)
    calendar_days = serializers.IntegerField(read_only=True)
    range_with_days = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'employee_name', 'leave_type_name', 'start_date', 
            'end_date', 'total_days', 'working_days', 'calendar_days', 'range_with_days',
            'status', 'status_display', 'created_at'
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