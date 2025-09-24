from rest_framework import serializers
from .models import Department, CustomUser as User

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'description']

class UserSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)
    department_id = serializers.IntegerField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False)
    # Expose superuser flag for frontend role-based UI (read-only)
    is_superuser = serializers.BooleanField(read_only=True)
    profile_image = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'employee_id', 'role', 'department', 'department_id',
            'phone', 'hire_date', 'annual_leave_entitlement',
            'is_active_employee', 'date_joined', 'password', 'profile_image',
            'is_superuser'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
        }
        read_only_fields = ['is_superuser']
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        department_id = validated_data.pop('department_id', None)
        
        user = User.objects.create_user(**validated_data)
        
        if password:
            user.set_password(password)
            user.save()
            
        if department_id:
            # Assign foreign key id via setattr to satisfy static analyzers
            setattr(user, 'department_id', department_id)
            user.save()
            
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        department_id = validated_data.pop('department_id', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        if password:
            instance.set_password(password)
            
        if department_id:
            # Assign foreign key id via setattr to satisfy static analyzers
            setattr(instance, 'department_id', department_id)
            
        instance.save()
        return instance