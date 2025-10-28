from rest_framework import serializers
from .models import Department, CustomUser as User, EmploymentGrade, Affiliate


class AffiliateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Affiliate
        fields = ['id', 'name', 'description']

class DepartmentSerializer(serializers.ModelSerializer):
    manager = serializers.SerializerMethodField(read_only=True)  # backward-compat alias of HOD
    affiliate = serializers.SerializerMethodField(read_only=True)
    affiliate_id = serializers.PrimaryKeyRelatedField(
        queryset=Affiliate.objects.all(), source='affiliate', required=False, allow_null=True, write_only=True
    )

    class Meta:
        model = Department
        fields = [
            'id', 'name', 'description',
            'approval_flow',
            'manager',  # alias for hod for existing UI
            'affiliate', 'affiliate_id',
        ]

    def get_manager(self, obj):
        hod = getattr(obj, 'hod', None)
        if not hod:
            return None
        return {
            'id': hod.pk,
            'name': hod.get_full_name(),
            'employee_id': hod.employee_id,
            'email': hod.email,
        }

    def get_affiliate(self, obj):
        aff = getattr(obj, 'affiliate', None)
        if not aff:
            return None
        return {
            'id': aff.pk,
            'name': aff.name,
        }

class UserSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)
    department_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    affiliate_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    password = serializers.CharField(write_only=True, required=False)
    is_superuser = serializers.BooleanField(read_only=True)
    profile_image = serializers.ImageField(required=False, allow_null=True)
    grade = serializers.SerializerMethodField(read_only=True)
    grade_id = serializers.PrimaryKeyRelatedField(
        queryset=EmploymentGrade.objects.filter(is_active=True), source='grade', allow_null=True, required=False, write_only=True
    )
    role_display = serializers.SerializerMethodField(read_only=True)

    def get_grade(self, obj):
        if obj.grade:
            return {'id': obj.grade.id, 'name': obj.grade.name, 'slug': obj.grade.slug}
        return None
    
    def get_role_display(self, obj):
        return obj.get_role_display_name()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'employee_id', 'role', 'role_display', 'department', 'department_id', 'affiliate_id',
            'phone', 'hire_date', 'annual_leave_entitlement',
            'is_active_employee', 'date_joined', 'password', 'profile_image',
            'is_superuser', 'grade', 'grade_id'
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'username': {'required': False},
            'employee_id': {'required': False},
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
        read_only_fields = ['is_superuser']
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        department_id = validated_data.pop('department_id', None)
        affiliate_id = validated_data.pop('affiliate_id', None)
        
        # Auto-generate username from email if not provided
        if 'username' not in validated_data or not validated_data.get('username'):
            base_username = validated_data['email'].split('@')[0]
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            validated_data['username'] = username
        
        # Auto-generate employee_id if not provided
        if 'employee_id' not in validated_data or not validated_data.get('employee_id'):
            # Generate format: EMP-YYYY-NNNN
            from django.utils import timezone
            year = timezone.now().year
            last_emp = User.objects.filter(employee_id__startswith=f'EMP-{year}').order_by('-employee_id').first()
            if last_emp and last_emp.employee_id:
                try:
                    last_num = int(last_emp.employee_id.split('-')[-1])
                    new_num = last_num + 1
                except:
                    new_num = 1
            else:
                new_num = 1
            validated_data['employee_id'] = f'EMP-{year}-{new_num:04d}'
        
        user = User.objects.create_user(**validated_data)
        
        if password:
            user.set_password(password)
            user.save()
        
        # Handle affiliate assignment
        if affiliate_id and not department_id:
            # For SDSL/SBL, assign to Executive department of that affiliate
            try:
                from users.models import Affiliate, Department
                affiliate = Affiliate.objects.get(pk=affiliate_id)
                exec_dept = Department.objects.filter(name='Executive', affiliate=affiliate).first()
                if exec_dept:
                    user.department = exec_dept
                    user.save()
            except:
                pass
            
        if department_id:
            # Assign foreign key id via setattr to satisfy static analyzers
            setattr(user, 'department_id', department_id)
            user.save()
            
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        department_id = validated_data.pop('department_id', None)
        
        # Special handling: allow clearing profile image by sending empty value
        if 'profile_image' in validated_data:
            img_val = validated_data.get('profile_image')
            if not img_val:  # '', None, False => clear
                validated_data['profile_image'] = None

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        if password:
            instance.set_password(password)
            
        if department_id:
            # Assign foreign key id via setattr to satisfy static analyzers
            setattr(instance, 'department_id', department_id)
            
        instance.save()
        return instance