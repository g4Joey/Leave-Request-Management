from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from typing import cast
from .models import CustomUser, Department
from .serializers import UserSerializer, DepartmentSerializer

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
        
        departments = Department.objects.all()
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
                'staff_count': len(staff_data),
                'staff': staff_data
            })
        
        return Response(data)
    
    def post(self, request):
        """Create a new employee (HR only)"""
        user = request.user
        role = getattr(user, 'role', None)
        if not (getattr(user, 'is_superuser', False) or (role in ['hr', 'admin'])):
            return Response(
                {"error": "Only HR can create employees"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
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
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsHRPermission]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]


class IsHRPermission(permissions.BasePermission):
    """
    Custom permission to only allow HR users to perform certain actions
    """
    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        user = request.user
        role = getattr(user, 'role', None)
        return bool(getattr(user, 'is_superuser', False) or (role in ['hr', 'admin']))
