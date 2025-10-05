"""
Views for role-based leave entitlement management.
Allows HR to configure leave entitlements by role (Junior Staff, Senior Staff, etc.)
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.contrib.auth import get_user_model

from leaves.models import LeaveType, LeaveBalance
from users.models import CustomUser
from leaves.serializers import LeaveTypeSerializer


class RoleEntitlementViewSet(viewsets.ViewSet):
    """
    ViewSet for managing role-based leave entitlements.
    HR can configure entitlements for different roles (junior_staff, senior_staff, etc.)
    """
    permission_classes = [IsAuthenticated]

    def _is_hr(self, request) -> bool:
        """Check if user is HR or admin"""
        user = request.user
        return getattr(user, 'is_superuser', False) or (
            hasattr(user, 'role') and getattr(user, 'role') in ['hr', 'admin']
        )

    def list(self, request):
        """Get list of all roles and their current entitlements"""
        if not self._is_hr(request):
            return Response({'detail': 'Only HR can access this resource'}, status=status.HTTP_403_FORBIDDEN)

        User = get_user_model()
        current_year = timezone.now().year
        
        # Get all role choices
        role_choices = CustomUser.ROLE_CHOICES
        leave_types = LeaveType.objects.filter(is_active=True)
        
        roles_data = []
        for role_code, role_display in role_choices:
            # Get users with this role
            users_with_role = User.objects.filter(
                role=role_code, 
                is_active=True, 
                is_active_employee=True
            )
            user_count = users_with_role.count()
            
            # Get current entitlements for this role (sample from first user)
            entitlements = {}
            if user_count > 0:
                sample_user = users_with_role.first()
                balances = LeaveBalance.objects.filter(
                    employee=sample_user,
                    year=current_year
                ).select_related('leave_type')
                
                for balance in balances:
                    entitlements[balance.leave_type.id] = {
                        'leave_type_id': balance.leave_type.id,
                        'leave_type_name': balance.leave_type.name,
                        'entitled_days': balance.entitled_days
                    }
            
            # Fill in missing leave types with 0
            for leave_type in leave_types:
                if leave_type.id not in entitlements:
                    entitlements[leave_type.id] = {
                        'leave_type_id': leave_type.id,
                        'leave_type_name': leave_type.name,
                        'entitled_days': 0
                    }
            
            roles_data.append({
                'role_code': role_code,
                'role_display': role_display,
                'user_count': user_count,
                'entitlements': list(entitlements.values())
            })
        
        return Response({
            'roles': roles_data,
            'leave_types': LeaveTypeSerializer(leave_types, many=True).data
        })

    @action(detail=False, methods=['post'], url_path=r'(?P<role_code>[^/.]+)/set_entitlements')
    def set_role_entitlements(self, request, role_code=None):
        """
        Set entitlements for all users with a specific role.
        Body: { "entitlements": [{"leave_type_id": 1, "entitled_days": 25}, ...] }
        """
        if not self._is_hr(request):
            return Response({'detail': 'Only HR can perform this action'}, status=status.HTTP_403_FORBIDDEN)

        # Validate role
        valid_roles = [choice[0] for choice in CustomUser.ROLE_CHOICES]
        if role_code not in valid_roles:
            return Response({'error': f'Invalid role: {role_code}'}, status=status.HTTP_400_BAD_REQUEST)

        entitlements_data = request.data.get('entitlements', [])
        if not isinstance(entitlements_data, list):
            return Response({'error': 'entitlements must be a list'}, status=status.HTTP_400_BAD_REQUEST)

        User = get_user_model()
        current_year = timezone.now().year
        
        # Get all users with this role
        users_with_role = User.objects.filter(
            role=role_code,
            is_active=True,
            is_active_employee=True
        )
        
        if users_with_role.count() == 0:
            return Response({'error': f'No active users found with role: {role_code}'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate entitlements data
        errors = []
        entitlements_to_apply = []
        
        for idx, entitlement in enumerate(entitlements_data):
            try:
                leave_type_id = int(entitlement.get('leave_type_id'))
                entitled_days = int(entitlement.get('entitled_days', 0))
            except (TypeError, ValueError):
                errors.append({'index': idx, 'error': 'leave_type_id and entitled_days must be integers'})
                continue
            
            if entitled_days < 0:
                errors.append({'index': idx, 'error': 'entitled_days must be non-negative'})
                continue
            
            try:
                leave_type = LeaveType.objects.get(pk=leave_type_id, is_active=True)
                entitlements_to_apply.append((leave_type, entitled_days))
            except LeaveType.DoesNotExist:
                errors.append({'index': idx, 'error': f'LeaveType {leave_type_id} not found or inactive'})
                continue

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        # Apply entitlements to all users with this role
        updated_count = 0
        created_count = 0
        
        for user in users_with_role:
            for leave_type, entitled_days in entitlements_to_apply:
                balance, was_created = LeaveBalance.objects.get_or_create(
                    employee=user,
                    leave_type=leave_type,
                    year=current_year,
                    defaults={
                        'entitled_days': entitled_days,
                        'used_days': 0,
                        'pending_days': 0
                    }
                )
                
                if was_created:
                    created_count += 1
                elif balance.entitled_days != entitled_days:
                    balance.entitled_days = entitled_days
                    balance.save(update_fields=['entitled_days', 'updated_at'])
                    updated_count += 1

        return Response({
            'message': f'Entitlements updated for role: {role_code}',
            'role_code': role_code,
            'users_affected': users_with_role.count(),
            'balances_updated': updated_count,
            'balances_created': created_count,
            'year': current_year
        })

    @action(detail=False, methods=['get'], url_path=r'(?P<role_code>[^/.]+)/summary')
    def role_summary(self, request, role_code=None):
        """Get summary for a specific role"""
        if not self._is_hr(request):
            return Response({'detail': 'Only HR can access this resource'}, status=status.HTTP_403_FORBIDDEN)

        # Validate role
        valid_roles = [choice[0] for choice in CustomUser.ROLE_CHOICES]
        if role_code not in valid_roles:
            return Response({'error': f'Invalid role: {role_code}'}, status=status.HTTP_400_BAD_REQUEST)

        User = get_user_model()
        current_year = timezone.now().year
        
        users_with_role = User.objects.filter(
            role=role_code,
            is_active=True,
            is_active_employee=True
        )
        
        role_display = dict(CustomUser.ROLE_CHOICES).get(role_code, role_code)
        
        # Get leave types and current entitlements
        leave_types = LeaveType.objects.filter(is_active=True)
        entitlements = []
        
        if users_with_role.exists():
            sample_user = users_with_role.first()
            balances = LeaveBalance.objects.filter(
                employee=sample_user,
                year=current_year
            ).select_related('leave_type')
            
            balance_dict = {b.leave_type.id: b.entitled_days for b in balances}
            
            for leave_type in leave_types:
                entitlements.append({
                    'leave_type_id': leave_type.id,
                    'leave_type_name': leave_type.name,
                    'entitled_days': balance_dict.get(leave_type.id, 0)
                })
        else:
            for leave_type in leave_types:
                entitlements.append({
                    'leave_type_id': leave_type.id,
                    'leave_type_name': leave_type.name,
                    'entitled_days': 0
                })

        return Response({
            'role_code': role_code,
            'role_display': role_display,
            'user_count': users_with_role.count(),
            'entitlements': entitlements,
            'year': current_year
        })