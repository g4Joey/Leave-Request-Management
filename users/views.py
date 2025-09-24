from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
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
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
                
                staff_data.append({
                    'id': staff.pk,
                    'employee_id': staff.employee_id,
                    'name': staff.get_full_name(),
                    'email': staff.email,
                    'role': staff.role,
                    'hire_date': staff.hire_date,
                    'manager': manager_info
                })
            
            data.append({
                'id': dept.pk,
                'name': dept.name,
                'description': dept.description,
                'staff_count': len(staff_data),
                'staff': staff_data
            })
        
        return Response(data)
