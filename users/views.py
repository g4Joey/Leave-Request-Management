from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from typing import cast
from .models import CustomUser, Department, Affiliate
from .serializers import UserSerializer, DepartmentSerializer, AffiliateSerializer

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users
    """
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        user = request.user
        if getattr(user, 'is_superuser', False) or getattr(user, 'role', None) in ['manager', 'hr', 'admin']:
            qs = CustomUser.objects.all()
        else:
            qs = CustomUser.objects.filter(pk=user.pk)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        user = request.user
        allowed_all = getattr(user, 'is_superuser', False) or getattr(user, 'role', None) in ['manager', 'hr', 'admin']
        if not allowed_all:
            # Only allow fetching own record
            if str(kwargs.get('pk')) != str(user.pk):
                return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)
        return super().retrieve(request, *args, **kwargs)

class UserProfileView(APIView):
    """
    View for getting/updating user profile
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MyProfileView(APIView):
    """Current user's profile management with image upload support"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"MyProfileView PATCH - Request data: {request.data}")
        logger.info(f"MyProfileView PATCH - Content type: {request.content_type}")
        logger.info(f"MyProfileView PATCH - Files: {request.FILES}")
        
        # Special case: explicit image removal (frontend sends empty string)
        if 'profile_image' in request.data and request.data.get('profile_image') in ['', None]:
            logger.info("MyProfileView PATCH - Clearing profile image as empty value provided")
            if getattr(request.user, 'profile_image', None):
                try:
                    request.user.profile_image.delete(save=False)
                except Exception as e:  # pragma: no cover - defensive
                    logger.warning(f"Failed deleting old image file: {e}")
            request.user.profile_image = None
            request.user.save(update_fields=["profile_image", "updated_at"]) if hasattr(request.user, 'updated_at') else request.user.save()
            refreshed = UserSerializer(request.user).data
            logger.info("MyProfileView PATCH - Image cleared successfully")
            return Response(refreshed)

        # Check if this is an image upload
        if 'profile_image' in request.FILES:
            image_file = request.FILES['profile_image']
            logger.info(f"MyProfileView PATCH - Image upload detected:")
            logger.info(f"  - Name: {image_file.name}")
            logger.info(f"  - Size: {image_file.size}")
            logger.info(f"  - Content type: {image_file.content_type}")
        
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            request.user.refresh_from_db()  # Refresh to get updated data
            logger.info(f"MyProfileView PATCH - Success: {serializer.data}")
            logger.info(f"MyProfileView PATCH - User profile_image after save: {request.user.profile_image}")
            return Response(serializer.data)
        
        logger.error(f"MyProfileView PATCH - Validation errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """Change password for the current user"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        if not current_password or not new_password:
            return Response(
                {'error': 'Both current_password and new_password are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        if not user.check_password(current_password):
            return Response(
                {'error': 'Current password is incorrect'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(new_password) < 8:
            return Response(
                {'error': 'New password must be at least 8 characters long'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(new_password)
        user.save()
        
        return Response({'message': 'Password changed successfully'})


class StaffManagementView(APIView):
    """
    View for HR staff management - view departments and staff
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get all departments with their staff members"""
        # Cast to CustomUser to access role attribute
        user = request.user
        role = getattr(user, 'role', None)
        if not (getattr(user, 'is_superuser', False) or (role in ['hr', 'admin'])):
            return Response(
                {"error": "Only HR can access staff information"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        departments = Department.objects.select_related('affiliate', 'hod').all()
        data = []
        
        import os
        show_demo = os.environ.get('SHOW_DEMO_USERS') == '1'
        for dept in departments:
            staff_qs = CustomUser.objects.filter(department=dept, is_active_employee=True)
            if not show_demo:
                staff_qs = staff_qs.exclude(is_demo=True)
            staff_members = staff_qs
            staff_data = []
            
            for staff in staff_members:
                manager_info = None
                if staff.manager:
                    manager_info = {
                        'id': staff.manager.pk,
                        'name': staff.manager.get_full_name(),
                        'employee_id': staff.manager.employee_id
                    }

                grade = getattr(staff, 'grade', None)
                grade_info = None
                if grade is not None:
                    grade_info = {
                        'id': getattr(grade, 'pk', None),
                        'name': getattr(grade, 'name', None),
                        'slug': getattr(grade, 'slug', None),
                    }
                
                staff_data.append({
                    'id': staff.pk,
                    'employee_id': staff.employee_id,
                    'name': staff.get_full_name(),
                    'email': staff.email,
                    'role': staff.role,
                    'hire_date': staff.hire_date,
                    'manager': manager_info,
                    'grade': grade_info,
                    'grade_id': getattr(staff, 'grade_id', None)
                })
            
            data.append({
                'id': dept.pk,
                'name': dept.name,
                'description': dept.description,
                'affiliate': (
                    {'id': dept.affiliate_id, 'name': dept.affiliate.name}
                    if getattr(dept, 'affiliate', None) else None
                ),
                'staff_count': len(staff_data),
                'staff': staff_data,
                # Keep key name 'manager' for backward-compatible API, but source from HOD field
                'manager': {
                    'id': dept.hod.pk,
                    'name': dept.hod.get_full_name(),
                    'employee_id': dept.hod.employee_id,
                    'email': dept.hod.email
                } if getattr(dept, 'hod', None) else None
            })
        
        return Response(data)
    
    def post(self, request):
        """Create a new employee (HR only) with auto-department creation"""
        user = request.user
        role = getattr(user, 'role', None)
        if not (getattr(user, 'is_superuser', False) or (role in ['hr', 'admin'])):
            return Response(
                {"error": "Only HR can create employees"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Handle department auto-creation if needed
        data = request.data.copy()
        department_name = data.get('department_name')
        affiliate_id = data.get('affiliate_id')
        affiliate_name = data.get('affiliate_name')

        affiliate_obj = None
        if affiliate_id:
            affiliate_obj = Affiliate.objects.filter(pk=affiliate_id, is_active=True).first()
        elif affiliate_name:
            affiliate_obj, _ = Affiliate.objects.get_or_create(name=affiliate_name.strip(), defaults={'description': ''})
        else:
            # Default all legacy imports to Merban Capital if it exists
            affiliate_obj = Affiliate.objects.filter(name__iexact='Merban Capital').first()
        if department_name and not data.get('department_id'):
            # Try to find existing department
            department_qs = Department.objects.filter(name__iexact=department_name)
            if affiliate_obj:
                department_qs = department_qs.filter(affiliate=affiliate_obj)
            department = department_qs.first()
            if not department:
                # Create new department
                department = Department.objects.create(
                    name=department_name,
                    affiliate=affiliate_obj,
                    description=f"Auto-created during employee import"
                )
            data['department_id'] = department.id
        
        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            user_instance = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DepartmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing departments (HR only)
    """
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        """Only HR can create, update, or delete departments"""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'set_manager']:
            permission_classes = [permissions.IsAuthenticated, IsHRPermission]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['post'])
    def set_manager(self, request, pk=None):
        """Set the HOD (Manager) for a department. Endpoint name kept for compatibility."""
        department = self.get_object()
        manager_id = request.data.get('manager_id')
        
        if manager_id:
            try:
                manager = CustomUser.objects.get(pk=manager_id, is_active_employee=True)
                # Verify the user has manager role or is admin/superuser
                if manager.role not in ['manager', 'hr', 'admin'] and not manager.is_superuser:
                    return Response(
                        {'error': 'Selected user must have manager, hr, or admin role'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                department.hod = manager
            except CustomUser.DoesNotExist:
                return Response(
                    {'error': 'Manager not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Remove Manager
            department.hod = None
        
        department.save()
        
        # Return updated department info
        manager_info = None
        if getattr(department, 'hod', None):
            manager_info = {
                'id': department.hod.pk,
                'name': department.hod.get_full_name(),
                'employee_id': department.hod.employee_id,
                'email': department.hod.email
            }
        
        return Response({
            'message': 'Department manager updated successfully',
            'department': {
                'id': department.pk,
                'name': department.name,
                'affiliate': {'id': department.affiliate_id, 'name': department.affiliate.name} if department.affiliate_id else None,
                'manager': manager_info
            }
        })


class AffiliateViewSet(viewsets.ModelViewSet):
    """Minimal Affiliate CRUD for HR"""
    queryset = Affiliate.objects.filter(is_active=True)
    serializer_class = AffiliateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsHRPermission]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_role_choices(request):
    """Get available role choices with display names"""
    from .models import CustomUser
    
    role_choices = []
    for role_value, role_label in CustomUser.ROLE_CHOICES:
        # Create a temporary user instance to get display name
        temp_user = CustomUser(role=role_value)
        role_choices.append({
            'value': role_value,
            'label': role_label,  # Original label
            'display': temp_user.get_role_display_name()  # Custom display name
        })
    
    return Response(role_choices)


class IsHRPermission(permissions.BasePermission):
    """
    Custom permission to only allow HR users to perform certain actions
    """
    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        user = request.user
        role = getattr(user, 'role', None)
        return bool(getattr(user, 'is_superuser', False) or (role in ['hr', 'admin']))
