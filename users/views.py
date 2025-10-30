from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from .models import CustomUser, Department
from rest_framework.views import APIView
from django.conf import settings
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from typing import cast
from django.core.management import call_command
import io
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

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def role_summary(request):
    """HR-only: Return counts and user lists per role, plus HOD assignments.
    This helps diagnose role/visibility mismatches in production.
    """
    # Enforce HR/Admin permission
    user = request.user
    role = getattr(user, 'role', None)
    if not (getattr(user, 'is_superuser', False) or (role in ['hr', 'admin'])):
        return Response({"error": "Only HR can view role summary"}, status=status.HTTP_403_FORBIDDEN)

    # Build role summary
    items = {}
    # Use distinct roles present in DB to avoid relying on static choices
    distinct_roles = list(CustomUser.objects.values_list('role', flat=True).distinct())
    for r in distinct_roles:
        users_qs = CustomUser.objects.filter(role=r, is_active=True).select_related('department').order_by('last_name', 'first_name')
        items[r or ''] = {
            'count': users_qs.count(),
            'users': [
                {
                    'id': u.pk,
                    'name': u.get_full_name(),
                    'email': u.email,
                    'department': u.department.name if getattr(u, 'department', None) else None,
                }
                for u in users_qs
            ]
        }

    # Department HOD assignments snapshot
    hods = []
    for dept in Department.objects.select_related('hod').order_by('name'):
        if getattr(dept, 'hod', None):
            hods.append({
                'department': dept.name,
                'hod': {
                    'id': dept.hod.pk,
                    'name': dept.hod.get_full_name(),
                    'email': dept.hod.email,
                }
            })

    return Response({
        'roles': items,
        'hod_assignments': hods,
    })
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


class AdminResetPasswordView(APIView):
    """Admin/HR can reset any staff member's password"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        # Only HR and Admin can reset passwords
        if not (getattr(request.user, 'is_superuser', False) or 
                getattr(request.user, 'role', None) in ['hr', 'admin']):
            return Response(
                {'error': 'Only HR and Admin can reset passwords'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_password = request.data.get('new_password')
        if not new_password:
            return Response(
                {'error': 'new_password is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(new_password) < 8:
            return Response(
                {'error': 'Password must be at least 8 characters long'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            target_user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        target_user.set_password(new_password)
        target_user.save()
        
        return Response({
            'message': f'Password reset successfully for {target_user.get_full_name()}',
            'user_id': target_user.id,
            'username': target_user.username
        })


class AdminUpdateEmailView(APIView):
    """Admin/HR can update any staff member's email"""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, user_id):
        # Only HR and Admin can update emails
        if not (getattr(request.user, 'is_superuser', False) or 
                getattr(request.user, 'role', None) in ['hr', 'admin']):
            return Response(
                {'error': 'Only HR and Admin can update emails'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_email = request.data.get('email')
        if not new_email:
            return Response(
                {'error': 'email is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate email format
        if '@' not in new_email:
            return Response(
                {'error': 'Invalid email format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            target_user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check email uniqueness
        if CustomUser.objects.filter(email=new_email).exclude(pk=user_id).exists():
            return Response(
                {'error': 'Email already in use by another user'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_email = target_user.email
        target_user.email = new_email
        target_user.save()
        
        return Response({
            'message': f'Email updated successfully for {target_user.get_full_name()}',
            'user_id': target_user.id,
            'old_email': old_email,
            'new_email': new_email
        })


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
        # Only HR/Admin (and superusers) can access staff information
        if not (getattr(user, 'is_superuser', False) or (role in ['hr', 'admin'])):
            return Response(
                {"error": "Only HR can access staff information"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check for filtering parameters
        affiliate_id = request.GET.get('affiliate_id')
        role_filter = request.GET.get('role')
        
        import os
        # Control demo user visibility:
        # - SHOW_DEMO_USERS=1 forces inclusion
        # - EXCLUDE_DEMO_USERS=1 forces exclusion
        # - Otherwise: default behavior excludes demo when DEBUG is False (production), includes in DEBUG
        show_demo_env = os.environ.get('SHOW_DEMO_USERS')
        exclude_demo_env = os.environ.get('EXCLUDE_DEMO_USERS')
        if show_demo_env == '1':
            exclude_demo = False
        elif exclude_demo_env == '1':
            exclude_demo = True
        else:
            # Default: hide demo users in production
            exclude_demo = not bool(getattr(settings, 'DEBUG', False))
        
        # If requesting CEOs specifically, handle that separately
        if role_filter == 'ceo':
            ceo_qs = CustomUser.objects.filter(role='ceo', is_active=True)
            if affiliate_id:
                # Match either direct user.affiliate or via their department's affiliate
                from django.db.models import Q as _Q
                ceo_qs = ceo_qs.filter(_Q(affiliate_id=affiliate_id) | _Q(department__affiliate_id=affiliate_id))
            
            if exclude_demo:
                ceo_qs = ceo_qs.exclude(is_demo=True)
            
            ceo_data = []
            for ceo in ceo_qs:
                ceo_data.append({
                    'id': ceo.pk,
                    'employee_id': getattr(ceo, 'employee_id', None),
                    'name': ceo.get_full_name(),
                    'email': ceo.email,
                    'role': ceo.role,
                    'hire_date': ceo.hire_date,
                })
            
            return Response(ceo_data)
        
        if affiliate_id:
            # Filter departments by affiliate
            departments = Department.objects.select_related('hod').filter(affiliate_id=affiliate_id)
        else:
            departments = Department.objects.select_related('hod').all()
        
        data = []
        
        for dept in departments:
            # Use a simple, reliable filter to avoid missing users on legacy datasets
            staff_qs = CustomUser.objects.filter(
                department=dept,
                is_active=True,
            )
            # Apply demo exclusion policy decided above
            if exclude_demo:
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
                    'manager': manager_info,
                    # grades removed
                })
            
            data.append({
                'id': dept.pk,
                'name': dept.name,
                'description': dept.description,
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
        
        # Handle affiliate-specific individual employees (SDSL/SBL without departments)
        if affiliate_id:
            try:
                affiliate = Affiliate.objects.get(pk=affiliate_id)
                # For SDSL/SBL, include individual employees (no department, but with affiliate)
                if affiliate.name in ['SDSL', 'SBL']:
                    individual_qs = CustomUser.objects.filter(
                        affiliate_id=affiliate_id,
                        department__isnull=True,  # No department assignment
                        is_active=True
                    ).exclude(role='ceo')  # Exclude CEOs as they're handled separately
                    
                    if exclude_demo:
                        individual_qs = individual_qs.exclude(is_demo=True)
                    
                    # Convert to list format similar to departments
                    individual_staff = []
                    for staff in individual_qs:
                        manager_info = None
                        if staff.manager:
                            manager_info = {
                                'id': staff.manager.pk,
                                'name': staff.manager.get_full_name(),
                                'employee_id': staff.manager.employee_id
                            }
                        
                        individual_staff.append({
                            'id': staff.pk,
                            'employee_id': staff.employee_id,
                            'name': staff.get_full_name(),
                            'email': staff.email,
                            'role': staff.role,
                            'hire_date': staff.hire_date,
                            'manager': manager_info,
                            # grades removed
                        })
                    
                    # Return individual employees as a flattened list for SDSL/SBL
                    if individual_staff:
                        return Response(individual_staff)
                        
            except Affiliate.DoesNotExist:
                pass
        
        # Additionally include CEOs (executives) as a top-level section so they appear
        # in the staff/department view even when they are individual entities (department=None).
        # This respects the same demo-exclusion policy used above.
        ceo_qs = CustomUser.objects.filter(role='ceo', is_active=True)
        if affiliate_id:
            ceo_qs = ceo_qs.filter(affiliate_id=affiliate_id)
        if exclude_demo:
            ceo_qs = ceo_qs.exclude(is_demo=True)
        ceo_list = []
        for ceo in ceo_qs:
            manager_info = None
            if ceo.manager:
                manager_info = {
                    'id': ceo.manager.pk,
                    'name': ceo.manager.get_full_name(),
                    'employee_id': ceo.manager.employee_id
                }
            ceo_list.append({
                'id': ceo.pk,
                'employee_id': getattr(ceo, 'employee_id', None),
                'name': ceo.get_full_name(),
                'email': ceo.email,
                'role': ceo.role,
                'hire_date': ceo.hire_date,
                'manager': manager_info,
                # grades removed
            })

        if ceo_list:
            data.append({
                'id': 'executives',
                'name': 'Executives',
                'description': 'Top-level executive users (CEOs)',
                'staff_count': len(ceo_list),
                'staff': ceo_list,
                'manager': None
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
        if department_name and not data.get('department_id'):
            # Try to find existing department
            department_qs = Department.objects.filter(name__iexact=department_name)
            department = department_qs.first()
            if not department:
                # Create new department
                department = Department.objects.create(
                    name=department_name,
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
    
    def get_queryset(self):
        qs = super().get_queryset()
        affiliate_id = self.request.query_params.get('affiliate_id')
        if affiliate_id:
            try:
                qs = qs.filter(affiliate_id=int(affiliate_id))
            except (TypeError, ValueError):
                qs = qs.none()
        return qs
    
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
                'manager': manager_info
            }
        })


## Affiliate endpoints removed


class AffiliateViewSet(viewsets.ModelViewSet):
    queryset = Affiliate.objects.all().order_by('name')
    serializer_class = AffiliateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsHRPermission]
        else:
            permission_classes = [permissions.IsAuthenticated, IsHRPermission]
        return [permission() for permission in permission_classes]

    def list(self, request, *args, **kwargs):
        # Auto-seed initial affiliates if none exist
        if Affiliate.objects.count() == 0:
            Affiliate.objects.bulk_create([
                Affiliate(name='MERBAN CAPITAL'),
                Affiliate(name='SDSL'),
                Affiliate(name='SBL'),
            ])
        return super().list(request, *args, **kwargs)


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


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsHRPermission])
def normalize_merban(request):
    """Admin-only: Run normalization to strip suffixes, merge duplicates, and link Merban departments.
    Returns the command output for visibility.
    """
    buf = io.StringIO()
    try:
        call_command('normalize_merban_departments', stdout=buf)
        out = buf.getvalue()
        return Response({"status": "ok", "output": out})
    except Exception as e:
        return Response({"status": "error", "error": str(e), "output": buf.getvalue()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
