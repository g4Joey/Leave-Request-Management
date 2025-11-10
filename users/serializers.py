from rest_framework import serializers
from .models import Department, CustomUser as User, Affiliate


class AffiliateSerializer(serializers.ModelSerializer):
    ceo = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Affiliate
        fields = ['id', 'name', 'description', 'ceo']

    def get_ceo(self, obj):
        # Return the first active CEO linked to this affiliate either directly or via department
        from .models import CustomUser as User
        from django.db.models import Q
        ceo = (
            User.objects.filter(role='ceo', is_active=True)
            .filter(Q(affiliate=obj) | Q(department__affiliate=obj))
            .order_by('id')
            .first()
        )
        if not ceo:
            return None
        name = ceo.get_full_name().strip() if ceo.get_full_name() else ''
        return {
            'id': ceo.id,
            'name': name or (ceo.email or ceo.username),
            'email': ceo.email,
        }

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
    affiliate_id = serializers.SerializerMethodField(read_only=True)  # Changed to read-only method field
    affiliate_id_write = serializers.IntegerField(write_only=True, required=False, allow_null=True, source='affiliate_id')
    affiliate = serializers.SerializerMethodField(read_only=True)
    affiliate_name = serializers.SerializerMethodField(read_only=True)
    password = serializers.CharField(write_only=True, required=False)
    is_superuser = serializers.BooleanField(read_only=True)
    profile_image = serializers.ImageField(required=False, allow_null=True)
    role_display = serializers.SerializerMethodField(read_only=True)

    def get_role_display(self, obj):
        return obj.get_role_display_name()

    def get_affiliate_id(self, obj):
        """Get user's affiliate ID with consistent logic"""
        if obj.department and obj.department.affiliate:
            return obj.department.affiliate.id
        elif obj.affiliate:
            return obj.affiliate.id
        return None

    def get_affiliate(self, obj):
        """Get user's affiliate with consistent logic: department affiliate first, then direct affiliate"""
        affiliate = None
        if obj.department and obj.department.affiliate:
            affiliate = obj.department.affiliate
        elif obj.affiliate:
            affiliate = obj.affiliate
        
        if affiliate:
            return {
                'id': affiliate.id,
                'name': affiliate.name
            }
        return None

    def get_affiliate_name(self, obj):
        """Get user's affiliate name - simplified for frontend compatibility"""
        if obj.department and obj.department.affiliate:
            return obj.department.affiliate.name
        elif obj.affiliate:
            return obj.affiliate.name
        return None

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'employee_id', 'role', 'role_display', 'department', 'department_id', 'affiliate_id_write',
            'affiliate_id', 'affiliate', 'affiliate_name',  # Added affiliate information
            'phone', 'hire_date', 'annual_leave_entitlement',
            'is_active_employee', 'date_joined', 'password', 'profile_image',
            'is_superuser'
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
        
        # Handle affiliate assignment (no automatic department assignment for affiliate-only users)
        if affiliate_id:
            # Assign foreign key id via setattr to satisfy static analyzers
            setattr(user, 'affiliate_id', affiliate_id)
            user.save(update_fields=['affiliate'])
            
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