from django.shortcuts import render
from typing import Any

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import LeaveRequest, LeaveType, LeaveBalance, LeaveGradeEntitlement
from .serializers import (
    LeaveRequestSerializer, 
    LeaveRequestListSerializer,
    LeaveApprovalSerializer,
    LeaveTypeSerializer, 
    LeaveBalanceSerializer,
    EmploymentGradeSerializer,
    LeaveGradeEntitlementSerializer
)
from users.models import EmploymentGrade
from .grade_entitlements import apply_grade_entitlements


class LeaveTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for leave types - read only for employees.
    HR-only actions provided for configuring global entitlements per leave type.
    """
    queryset = LeaveType.objects.filter(is_active=True)
    serializer_class = LeaveTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _is_hr(self, request) -> bool:
        user = request.user
        # Narrow user type to CustomUser when possible to satisfy static analysis
        try:
            from users.models import CustomUser  # local import to avoid circulars at import time
            if isinstance(user, CustomUser):
                return user.is_superuser or user.role in ['hr', 'admin']
        except Exception:
            pass
        # Fallback to permissive attribute checks
        return getattr(user, 'is_superuser', False) or (
            hasattr(user, 'role') and getattr(user, 'role') in ['hr', 'admin']
        )

    @action(detail=True, methods=['get'])
    def entitlement_summary(self, request, pk=None):
        """
        HR-only: Get a quick summary of current-year entitlements for this leave type.
        Returns the most common entitlement_days (mode) to prefill UI.
        """
        if not self._is_hr(request):
            return Response({'detail': 'Only HR can access this resource'}, status=status.HTTP_403_FORBIDDEN)

        leave_type = self.get_object()
        current_year = timezone.now().year
        qs = LeaveBalance.objects.filter(leave_type=leave_type, year=current_year)
        total = qs.count()
        mode_row = qs.values('entitled_days').annotate(cnt=Count('id')).order_by('-cnt').first()
        common_entitled_days = mode_row['entitled_days'] if mode_row else 0
        return Response({
            'leave_type': leave_type.name,
            'year': current_year,
            'total_balances': total,
            'common_entitled_days': common_entitled_days,
        })

    @action(detail=True, methods=['post'])
    def set_entitlement(self, request, pk=None):
        """
        HR-only: Set the entitled_days for all active employees for this leave type and current year.
        Creates missing LeaveBalance rows when necessary. Does not modify used/pending; remaining updates derive automatically.
        Body: { "entitled_days": <int> }
        """
        if not self._is_hr(request):
            return Response({'detail': 'Only HR can perform this action'}, status=status.HTTP_403_FORBIDDEN)

        try:
            entitled_days = int(request.data.get('entitled_days'))
        except (TypeError, ValueError):
            return Response({'error': 'entitled_days must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

        if entitled_days < 0:
            return Response({'error': 'entitled_days must be non-negative'}, status=status.HTTP_400_BAD_REQUEST)

        leave_type = self.get_object()
        current_year = timezone.now().year
        User = get_user_model()
        # Update active employees only (both Django active and domain-specific active)
        employees = User.objects.filter(is_active=True, is_active_employee=True)

        updated = 0
        created = 0
        balances = LeaveBalance.objects.filter(leave_type=leave_type, year=current_year)

        # Update existing balances
        for b in balances:
            if b.entitled_days != entitled_days:
                b.entitled_days = entitled_days
                b.save(update_fields=['entitled_days', 'updated_at'])
                updated += 1

        # Create missing balances for active employees
        existing_user_ids = set(b.employee_id for b in balances)
        to_create = []
        for emp in employees:
            if emp.id not in existing_user_ids:
                to_create.append(LeaveBalance(
                    employee=emp,
                    leave_type=leave_type,
                    year=current_year,
                    entitled_days=entitled_days,
                    used_days=0,
                    pending_days=0,
                ))
        if to_create:
            LeaveBalance.objects.bulk_create(to_create)
            created = len(to_create)

        return Response({
            'message': 'Entitlements updated',
            'leave_type': leave_type.name,
            'year': current_year,
            'updated': updated,
            'created': created,
            'entitled_days': entitled_days,
        })


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing leave balances - supports requirements R2, R3
    """
    serializer_class = LeaveBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['year', 'leave_type']
    
    def get_queryset(self):  # type: ignore[override]
        """Return balances for the current user only"""
        return LeaveBalance.objects.filter(employee=self.request.user)

    def _is_hr(self, request) -> bool:
        user = request.user
        try:
            from users.models import CustomUser
            if isinstance(user, CustomUser):
                return user.is_superuser or user.role in ['hr', 'admin']
        except Exception:
            pass
        return getattr(user, 'is_superuser', False) or (
            hasattr(user, 'role') and getattr(user, 'role') in ['hr', 'admin']
        )
    
    @action(detail=False, methods=['get'])
    def current_year(self, request):
        """Get leave balances for current year"""
        current_year = timezone.now().year
        balances = self.get_queryset().filter(year=current_year)
        serializer = self.get_serializer(balances, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def current_year_full(self, request):
        """
        Get current user's leave benefits for the current year, including all active leave types.
        Returns zeros for types without an existing balance. Useful for dashboard display.
        """
        user = request.user
        current_year = timezone.now().year
        types = list(LeaveType.objects.filter(is_active=True))
        balances = LeaveBalance.objects.filter(employee=user, year=current_year)
        by_lt = {getattr(b, 'leave_type_id'): b for b in balances}
        items = []
        for lt in types:
            b = by_lt.get(getattr(lt, 'id'))
            entitled = b.entitled_days if b else 0
            used = b.used_days if b else 0
            pending = b.pending_days if b else 0
            remaining = max(0, entitled - used - pending)
            items.append({
                'leave_type': {
                    'id': getattr(lt, 'id'),
                    'name': lt.name,
                },
                'entitled_days': entitled,
                'used_days': used,
                'pending_days': pending,
                'remaining_days': remaining,
                'year': current_year,
            })
        return Response(items)

    @action(detail=False, methods=['get'], url_path=r'employee/(?P<employee_id>[^/.]+)/current_year')
    def employee_current_year(self, request, employee_id: str):
        """
        HR-only: Get leave benefits for a specific employee for the current year,
        covering all active leave types (returns 0 for types without an existing balance).
        """
        if not self._is_hr(request):
            return Response({'detail': 'Only HR can access this resource'}, status=status.HTTP_403_FORBIDDEN)

        User = get_user_model()
        try:
            employee = User.objects.get(pk=employee_id, is_active=True)
        except User.DoesNotExist:
            return Response({'detail': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)

        current_year = timezone.now().year
        types = list(LeaveType.objects.filter(is_active=True))
        balances = LeaveBalance.objects.filter(employee=employee, year=current_year)
        # Use getattr to appease static analyzers about dynamic ORM fields
        by_lt = {getattr(b, 'leave_type_id'): b for b in balances}
        items = []
        for lt in types:
            b = by_lt.get(getattr(lt, 'id'))
            items.append({
                'leave_type': {
                    'id': getattr(lt, 'id'),
                    'name': lt.name,
                    'description': lt.description,
                },
                'entitled_days': b.entitled_days if b else 0,
            })
        return Response({'employee_id': getattr(employee, 'id'), 'year': current_year, 'items': items})

    @action(detail=False, methods=['post'], url_path=r'employee/(?P<employee_id>[^/.]+)/set_entitlements')
    def set_employee_entitlements(self, request, employee_id: str):
        """
        HR-only: Set per-employee entitlements for the current year.
        Body: { "items": [ { "leave_type": <id>, "entitled_days": <int> }, ... ] }
        """
        if not self._is_hr(request):
            return Response({'detail': 'Only HR can perform this action'}, status=status.HTTP_403_FORBIDDEN)

        payload = request.data or {}
        items = payload.get('items')
        if not isinstance(items, list):
            return Response({'error': 'items must be a list'}, status=status.HTTP_400_BAD_REQUEST)

        User = get_user_model()
        try:
            employee = User.objects.get(pk=employee_id, is_active=True)
        except User.DoesNotExist:
            return Response({'detail': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)

        current_year = timezone.now().year
        updated = 0
        created = 0
        errors = []

        for idx, it in enumerate(items):
            try:
                lt_id = int(it.get('leave_type'))
                days = int(it.get('entitled_days'))
            except Exception:
                errors.append({'index': idx, 'error': 'leave_type and entitled_days must be integers'})
                continue
            if days < 0:
                errors.append({'index': idx, 'error': 'entitled_days must be non-negative'})
                continue

            try:
                lt = LeaveType.objects.get(pk=lt_id, is_active=True)
            except LeaveType.DoesNotExist:
                errors.append({'index': idx, 'error': f'LeaveType {lt_id} not found or inactive'})
                continue

            b, was_created = LeaveBalance.objects.get_or_create(
                employee=employee,
                leave_type=lt,
                year=current_year,
                defaults={'entitled_days': days}
            )
            if was_created:
                created += 1
            else:
                if b.entitled_days != days:
                    b.entitled_days = days
                    b.save(update_fields=['entitled_days', 'updated_at'])
                    updated += 1

        return Response({
            'message': 'Entitlements updated',
            'employee_id': getattr(employee, 'id'),
            'year': current_year,
            'updated': updated,
            'created': created,
            'errors': errors,
        })
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary of all leave balances for dashboard - supports R2"""
        current_year = timezone.now().year
        balances = self.get_queryset().filter(year=current_year)
        
        summary_data = {
            'year': current_year,
            'total_entitled': sum(b.entitled_days for b in balances),
            'total_used': sum(b.used_days for b in balances),
            'total_pending': sum(b.pending_days for b in balances),
            'total_remaining': sum(b.remaining_days for b in balances),
            'by_leave_type': []
        }
        
        for balance in balances:
            summary_data['by_leave_type'].append({
                'leave_type': balance.leave_type.name,
                'entitled': balance.entitled_days,
                'used': balance.used_days,
                'pending': balance.pending_days,
                'remaining': balance.remaining_days
            })
        
        return Response(summary_data)


class LeaveRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for leave requests - supports requirements R1, R12
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'leave_type', 'start_date', 'end_date']
    search_fields = ['reason', 'approval_comments']
    ordering_fields = ['created_at', 'start_date', 'end_date']
    ordering = ['-created_at']
    
    def get_queryset(self):  # type: ignore[override]
        """Return leave requests for the current user"""
        return LeaveRequest.objects.filter(employee=self.request.user)
    
    def get_serializer_class(self):  # type: ignore[override]
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return LeaveRequestListSerializer
        elif self.action in ['approve', 'reject']:
            return LeaveApprovalSerializer
        return LeaveRequestSerializer
    
    def perform_create(self, serializer):
        """Set the employee to current user when creating - supports R1"""
        import logging
        from notifications.services import LeaveNotificationService
        logger = logging.getLogger('leaves')
        
        user = self.request.user
        try:
            logger.info(f'Creating leave request for user: {user.username} (ID: {getattr(user, "id", "unknown")})')
            
            # Log the validated data for debugging
            logger.info(f'Leave request data: {serializer.validated_data}')
            
            leave_request = serializer.save(employee=user)
            logger.info(f'Leave request created successfully: ID={leave_request.id}')
            
            # Send notification to manager
            LeaveNotificationService.notify_leave_submitted(leave_request)
            logger.info(f'Notification sent for new leave request {leave_request.id}')
            
            # Recalculate balance for authoritative state
            try:
                balance = LeaveBalance.objects.get(
                    employee=leave_request.employee,
                    leave_type=leave_request.leave_type,
                    year=leave_request.start_date.year
                )
                balance.update_balance()
                logger.info(f'Updated leave balance for {balance.leave_type.name}: {balance.remaining_days} remaining')
            except LeaveBalance.DoesNotExist:
                logger.warning(f'No leave balance found for {user.username}, leave_type_id={leave_request.leave_type.id}, year={leave_request.start_date.year}')
                # Safety net: if no balance exists, skip
                pass
                
        except Exception as e:
            logger.error(f'Error creating leave request for {user.username}: {str(e)}', exc_info=True)
            raise
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending leave requests for current user"""
        pending_requests = self.get_queryset().filter(status='pending')
        serializer = self.get_serializer(pending_requests, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def approved(self, request):
        """Get approved leave requests for current user"""
        approved_requests = self.get_queryset().filter(status='approved')
        serializer = self.get_serializer(approved_requests, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get complete history of leave requests - supports R12"""
        # Get all requests with optional filtering
        year = request.query_params.get('year')
        if year:
            requests = self.get_queryset().filter(start_date__year=year)
        else:
            requests = self.get_queryset()
        
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get dashboard summary - supports R2"""
        current_year = timezone.now().year
        user_requests = self.get_queryset()
        
        # Calculate statistics
        total_requests = user_requests.count()
        pending_requests = user_requests.filter(status='pending').count()
        approved_requests = user_requests.filter(status='approved').count()
        rejected_requests = user_requests.filter(status='rejected').count()
        
        # Current year statistics
        current_year_requests = user_requests.filter(start_date__year=current_year)
        total_days_taken = sum(req.total_days or 0 for req in current_year_requests.filter(status='approved'))
        pending_days = sum(req.total_days or 0 for req in current_year_requests.filter(status='pending'))
        
        # Recent requests (last 5)
        recent_requests = user_requests[:5]
        recent_serializer = LeaveRequestListSerializer(recent_requests, many=True)
        
        dashboard_data = {
            'summary': {
                'total_requests': total_requests,
                'pending_requests': pending_requests,
                'approved_requests': approved_requests,
                'rejected_requests': rejected_requests,
                'total_days_taken_this_year': total_days_taken,
                'pending_days': pending_days,
            },
            'recent_requests': recent_serializer.data
        }
        
        return Response(dashboard_data)


class ManagerLeaveViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managers to view and approve leave requests - supports R4
    """
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'leave_type', 'start_date', 'employee']
    search_fields = ['employee__first_name', 'employee__last_name', 'reason']
    ordering_fields = ['created_at', 'start_date', 'end_date']
    ordering = ['-created_at']
    
    def get_queryset(self):  # type: ignore[override]
        """Return leave requests that this manager can approve"""
        user = self.request.user
        
        # For now, managers can see all requests
        # This can be enhanced with proper hierarchy later
        try:
            from users.models import CustomUser
            if isinstance(user, CustomUser):
                if user.is_superuser or user.role in ['manager', 'hr', 'ceo', 'admin']:
                    return LeaveRequest.objects.all()
                else:
                    return LeaveRequest.objects.none()
        except Exception:
            pass

        if getattr(user, 'is_superuser', False) or (
            hasattr(user, 'role') and getattr(user, 'role') in ['manager', 'hr', 'ceo', 'admin']
        ):
            return LeaveRequest.objects.all()
        else:
            # Regular employees can't access this endpoint
            return LeaveRequest.objects.none()
    
    def get_permissions(self):
        """Custom permissions for different actions"""
        if self.action in ['approve', 'reject']:
            permission_classes = [permissions.IsAuthenticated, IsManagerPermission]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """Get leave requests pending approval for current user's role"""
        user = request.user
        user_role = getattr(user, 'role', None)
        
        # Filter requests based on user's role and approval stage
        if user_role == 'manager':
            # Managers see requests pending their approval
            pending_requests = self.get_queryset().filter(status='pending')
        elif user_role == 'hr':
            # HR sees requests approved by manager
            pending_requests = self.get_queryset().filter(status='manager_approved')
        elif user_role == 'ceo':
            # CEO sees requests approved by HR
            pending_requests = self.get_queryset().filter(status='hr_approved')
        elif user_role == 'admin':
            # Admin sees all pending requests
            pending_requests = self.get_queryset().filter(status__in=['pending', 'manager_approved', 'hr_approved'])
        else:
            # No approval permissions
            pending_requests = self.get_queryset().none()
        
        serializer = self.get_serializer(pending_requests, many=True)
        
        # Add summary information
        response_data = {
            'requests': serializer.data,
            'count': len(serializer.data),
            'user_role': user_role,
            'approval_stage': {
                'manager': 'Initial Manager Approval',
                'hr': 'HR Review',
                'ceo': 'Final CEO Approval',
                'admin': 'Administrative Override'
            }.get(user_role, 'No approval permissions')
        }
        
        return Response(response_data)
    
    @action(detail=True, methods=['put'])
    def approve(self, request, pk=None):
        """Multi-stage approval system: Manager → HR → CEO"""
        import logging
        from notifications.services import LeaveNotificationService
        logger = logging.getLogger('leaves')
        
        try:
            leave_request = self.get_object()
            user = request.user
            comments = request.data.get('approval_comments', '')
            
            logger.info(f'Attempting to approve leave request {pk} by user {user.username} (role: {getattr(user, "role", "unknown")})')
            
            # Check if request can be approved
            if leave_request.status == 'rejected':
                return Response({'error': 'Cannot approve a rejected request'}, status=status.HTTP_400_BAD_REQUEST)
            elif leave_request.status == 'approved':
                return Response({'error': 'Request is already fully approved'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Determine approval action based on user role and current status
            user_role = getattr(user, 'role', None)
            
            if user_role == 'manager' and leave_request.status == 'pending':
                # Manager approval - move to HR stage
                leave_request.manager_approve(user, comments)
                LeaveNotificationService.notify_manager_approval(leave_request, user)
                message = 'Leave request approved by manager and forwarded to HR'
                logger.info(f'Manager approved leave request {pk}')
                
            elif user_role == 'hr' and leave_request.status == 'manager_approved':
                # HR approval - move to CEO stage
                leave_request.hr_approve(user, comments)
                LeaveNotificationService.notify_hr_approval(leave_request, user)
                message = 'Leave request approved by HR and forwarded to CEO'
                logger.info(f'HR approved leave request {pk}')
                
            elif user_role in ['ceo', 'admin'] and leave_request.status == 'hr_approved':
                # CEO final approval
                leave_request.ceo_approve(user, comments)
                LeaveNotificationService.notify_ceo_approval(leave_request, user)
                # Update leave balance only on final approval
                self._update_leave_balance(leave_request, 'approve')
                message = 'Leave request given final approval by CEO'
                logger.info(f'CEO gave final approval for leave request {pk}')
                
            elif user_role == 'admin':
                # Admin can approve at any stage (override)
                if leave_request.status == 'pending':
                    leave_request.manager_approve(user, f"ADMIN OVERRIDE: {comments}")
                if leave_request.status == 'manager_approved':
                    leave_request.hr_approve(user, f"ADMIN OVERRIDE: {comments}")
                if leave_request.status == 'hr_approved':
                    leave_request.ceo_approve(user, f"ADMIN OVERRIDE: {comments}")
                    self._update_leave_balance(leave_request, 'approve')
                LeaveNotificationService.notify_ceo_approval(leave_request, user)
                message = 'Leave request approved by admin (full override)'
                logger.info(f'Admin gave full approval override for leave request {pk}')
                
            else:
                # Invalid approval attempt
                current_stage = leave_request.current_approval_stage
                required_role = leave_request.next_approver_role
                return Response({
                    'error': f'Cannot approve this request. Current stage: {current_stage}, requires: {required_role}, your role: {user_role}'
                }, status=status.HTTP_403_FORBIDDEN)
            
            return Response({'message': message, 'current_status': leave_request.status})
                
        except Exception as e:
            logger.error(f'Error approving leave request {pk}: {str(e)}', exc_info=True)
            return Response({'error': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['put'])
    def reject(self, request, pk=None):
        """Reject a leave request at any stage"""
        import logging
        from notifications.services import LeaveNotificationService
        logger = logging.getLogger('leaves')
        
        try:
            leave_request = self.get_object()
            user = request.user
            comments = request.data.get('approval_comments', '')
            
            logger.info(f'Attempting to reject leave request {pk} by user {user.username} (role: {getattr(user, "role", "unknown")})')
            
            if leave_request.status in ['rejected', 'cancelled']:
                return Response({'error': 'Request is already rejected or cancelled'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Determine rejection stage based on user role and current status
            user_role = getattr(user, 'role', None)
            rejection_stage = None
            
            if user_role == 'manager' and leave_request.status == 'pending':
                rejection_stage = 'manager'
            elif user_role == 'hr' and leave_request.status in ['pending', 'manager_approved']:
                rejection_stage = 'hr'
            elif user_role in ['ceo', 'admin'] and leave_request.status in ['pending', 'manager_approved', 'hr_approved']:
                rejection_stage = user_role.replace('admin', 'ceo')  # Treat admin as CEO for rejection
            elif user_role == 'admin':
                # Admin can reject at any stage
                rejection_stage = 'admin'
            else:
                return Response({
                    'error': f'Cannot reject this request. Current stage: {leave_request.current_approval_stage}, your role: {user_role}'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Perform rejection
            leave_request.reject(user, comments, rejection_stage)
            
            # Send notifications
            LeaveNotificationService.notify_rejection(leave_request, user, rejection_stage)
            
            # Update leave balance (remove from pending)
            self._update_leave_balance(leave_request, 'reject')
            
            logger.info(f'Successfully rejected leave request {pk} at {rejection_stage} level')
            return Response({
                'message': f'Leave request rejected by {rejection_stage}',
                'current_status': leave_request.status
            })
                
        except Exception as e:
            logger.error(f'Error rejecting leave request {pk}: {str(e)}', exc_info=True)
            return Response({'error': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _update_leave_balance(self, leave_request, action):
        """Update leave balance based on approval/rejection"""
        import logging
        logger = logging.getLogger('leaves')
        
        try:
            logger.info(f'Updating leave balance for {action} action on request {leave_request.id}')
            balance = LeaveBalance.objects.get(
                employee=leave_request.employee,
                leave_type=leave_request.leave_type,
                year=leave_request.start_date.year
            )
            
            logger.info(f'Found balance for {leave_request.employee.username} - {leave_request.leave_type.name} - {leave_request.start_date.year}')
            
            # Recompute from source of truth to avoid negative values
            balance.update_balance()
            logger.info(f'Updated balance: entitled={balance.entitled_days}, used={balance.used_days}, pending={balance.pending_days}')
            
        except LeaveBalance.DoesNotExist:
            logger.warning(f'No leave balance found for {leave_request.employee.username} - {leave_request.leave_type.name} - {leave_request.start_date.year}')
            # Handle case where balance doesn't exist
            pass
        except Exception as e:
            logger.error(f'Error updating leave balance: {str(e)}', exc_info=True)
            raise


class IsManagerPermission(permissions.BasePermission):
    """
    Custom permission to only allow managers to approve/reject leaves
    """
    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        user = request.user
        try:
            from users.models import CustomUser
            if isinstance(user, CustomUser):
                return user.is_superuser or user.role in ['manager', 'hr', 'admin']
        except Exception:
            pass
        return getattr(user, 'is_superuser', False) or (
            hasattr(user, 'role') and getattr(user, 'role') in ['manager', 'hr', 'admin']
        )


class IsHRAdminPermission(permissions.BasePermission):
    """Permission limited strictly to HR/Admin (or superuser)."""
    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        user = request.user
        role = getattr(user, 'role', None)
        return bool(getattr(user, 'is_superuser', False) or role in ['hr', 'admin'])


class EmploymentGradeViewSet(viewsets.ModelViewSet):
    queryset = EmploymentGrade.objects.filter(is_active=True)
    serializer_class = EmploymentGradeSerializer
    # Default relaxed auth; enforce HR/Admin for mutating actions in get_permissions
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):  # type: ignore[override]
        """Allow any authenticated user to list/retrieve grades, but restrict write ops to HR/Admin."""
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        # For create/update/partial_update/destroy use HR/Admin gate
        return [permissions.IsAuthenticated(), IsHRAdminPermission()]


class LeaveGradeEntitlementViewSet(viewsets.ModelViewSet):
    queryset = LeaveGradeEntitlement.objects.select_related('grade', 'leave_type')
    serializer_class = LeaveGradeEntitlementSerializer
    permission_classes = [permissions.IsAuthenticated, IsHRAdminPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['grade', 'leave_type']

    @action(detail=False, methods=['post'])
    def bulk_set(self, request):
        """Bulk set entitlements for a grade.

        Body: { "grade_id": <id>, "items": [ {"leave_type_id": <id>, "entitled_days": <num>} ], "apply_now": true|false }
        """
        grade_id = request.data.get('grade_id')
        items = request.data.get('items', [])
        apply_now = bool(request.data.get('apply_now'))
        try:
            grade = EmploymentGrade.objects.get(pk=grade_id, is_active=True)
        except EmploymentGrade.DoesNotExist:
            return Response({'error': 'grade not found'}, status=404)

        updated = 0
        created = 0
        errors = []
        from decimal import Decimal
        for idx, it in enumerate(items):
            try:
                lt_id = int(it.get('leave_type_id'))
                days = Decimal(str(it.get('entitled_days')))
            except Exception:
                errors.append({'index': idx, 'error': 'invalid leave_type_id or entitled_days'})
                continue
            if days < 0:
                errors.append({'index': idx, 'error': 'entitled_days must be non-negative'})
                continue
            try:
                lt = LeaveType.objects.get(pk=lt_id, is_active=True)
            except LeaveType.DoesNotExist:
                errors.append({'index': idx, 'error': f'leave_type {lt_id} not found'})
                continue
            ent, created_flag = LeaveGradeEntitlement.objects.get_or_create(
                grade=grade, leave_type=lt, defaults={'entitled_days': days}
            )
            if created_flag:
                created += 1
            else:
                if ent.entitled_days != days:
                    ent.entitled_days = days
                    ent.save(update_fields=['entitled_days', 'updated_at'])
                    updated += 1

        applied = 0
        if apply_now:
            applied = apply_grade_entitlements(grade)

        return Response({
            'message': 'Grade entitlements processed',
            'grade': grade.name,
            'updated': updated,
            'created': created,
            'applied_to_balances': applied,
            'errors': errors,
        })

    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        grade = self.get_object().grade if isinstance(self.get_object(), LeaveGradeEntitlement) else None
        # If detail route on an entitlement record, apply for its grade; if we later add grade detail, adapt
        if not grade:
            return Response({'error': 'Unable to resolve grade from entitlement'}, status=400)
        applied = apply_grade_entitlements(grade)
        return Response({'message': 'Applied grade entitlements', 'grade': grade.name, 'applied_to_balances': applied})
