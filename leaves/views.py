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
        # Update active workers. Include domain-active employees and also HR/Managers/CEOs even if not flagged as active employees.
        # This ensures HODs or HR acting as managers receive updated entitlements too.
        employees = User.objects.filter(is_active=True).filter(
            Q(is_active_employee=True) | Q(role__in=['manager', 'hr', 'ceo'])
        )

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
        import logging
        logger = logging.getLogger('leaves')
        try:
            auth_present = 'HTTP_AUTHORIZATION' in request.META
            logger.info(f"current_year_full called - user={getattr(request, 'user', None)} auth_present={auth_present}")
        except Exception:
            logger.exception('Error logging current_year_full call')
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
            
            # Check if the user is a manager - if so, bypass manager approval and go straight to HR
            user_role = getattr(user, 'role', None)
            if user_role == 'manager':
                # Manager's own request should bypass manager stage and go directly to HR
                serializer.validated_data['status'] = 'manager_approved'
                logger.info(f'Manager {user.username} submitting own request - bypassing manager approval, going directly to HR')
            
            leave_request = serializer.save(employee=user)
            logger.info(f'Leave request created successfully: ID={leave_request.id}, status={leave_request.status}')
            
            # Send notification to manager
            LeaveNotificationService.notify_leave_submitted(leave_request)
            logger.info(f'Notification sent for new leave request {leave_request.id}')
            
            # Check for department-wide overlaps and notify if necessary
            try:
                from leaves.utils import find_overlaps, get_overlap_summary, should_trigger_overlap_notification
                
                if hasattr(leave_request.employee, 'department') and leave_request.employee.department:
                    overlaps = find_overlaps(
                        dept_id=leave_request.employee.department.id,
                        new_start=leave_request.start_date,
                        new_end=leave_request.end_date,
                        exclude_user_id=leave_request.employee.id
                    )
                    
                    if overlaps.exists():
                        overlap_summary = get_overlap_summary(overlaps, leave_request.start_date, leave_request.end_date)
                        
                        # Only notify if overlaps meet configured thresholds
                        if should_trigger_overlap_notification(overlap_summary):
                            LeaveNotificationService.notify_leave_overlap(leave_request, overlap_summary)
                            logger.info(f'Overlap notifications sent for leave request {leave_request.id}: {overlap_summary["total_overlaps"]} overlaps detected')
                        else:
                            logger.info(f'Overlap detected but below notification threshold for leave request {leave_request.id}')
                    
            except Exception as e:
                logger.error(f'Error checking overlaps for leave request {leave_request.id}: {str(e)}', exc_info=True)
                # Non-fatal error - don't break the leave creation process
            
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
        
        # Recent requests (last 5) with stage-aware labels
        recent_requests = user_requests[:5]
        recent_serializer = LeaveRequestListSerializer(recent_requests, many=True)
        recent_data = recent_serializer.data
        # Prefer stage_label when it indicates the next pending approver for better UX
        for item in recent_data:
            try:
                if item.get('stage_label') and item.get('status') in ['pending', 'manager_approved', 'hr_approved']:
                    item['status_display'] = item['stage_label']
            except Exception:
                # Non-fatal; keep default labels
                pass
        
        dashboard_data = {
            'summary': {
                'total_requests': total_requests,
                'pending_requests': pending_requests,
                'approved_requests': approved_requests,
                'rejected_requests': rejected_requests,
                'total_days_taken_this_year': total_days_taken,
                'pending_days': pending_days,
            },
            'recent_requests': recent_data
        }
        
        return Response(dashboard_data)


class ManagerLeaveViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Managers to view and approve leave requests - supports R4
    """
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'leave_type', 'start_date', 'employee']
    search_fields = ['employee__first_name', 'employee__last_name', 'reason']
    ordering_fields = ['created_at', 'start_date', 'end_date']
    ordering = ['-created_at']
    
    def get_queryset(self):  # type: ignore[override]
        """Return leave requests available to the current approver.

        Rules:
        - manager: only requests from their direct reports (employee__manager = self.user)
        - hr: all requests that are at or beyond Manager stage
        - ceo: all requests that are at or beyond HR stage
        - admin/superuser: all requests
        - others: none
        """
        user = self.request.user
        qs = LeaveRequest.objects.all()
        role = getattr(user, 'role', None)

        # Superuser/admin: full access
        if getattr(user, 'is_superuser', False) or role == 'admin':
            return qs

        if role == 'manager':
            # Direct reports or same department where user is HOD/Manager, but EXCLUDE own requests
            return qs.filter(
                Q(employee__manager=user) | Q(employee__department__hod=user)
            ).exclude(employee=user)

        if role == 'hr':
            # Items that have passed Manager stage or are pending (to allow visibility)
            return qs.filter(status__in=['pending', 'manager_approved', 'hr_approved', 'approved', 'rejected'])

        if role == 'ceo':
            # Items that require or have passed CEO stage. Include manager_approved for SDSL flow.
            return qs.filter(status__in=['manager_approved', 'hr_approved', 'approved', 'rejected'])

        # Everyone else: no access
        return qs.none()
    
    def get_permissions(self):
        """Custom permissions for different actions"""
        if self.action in ['approve', 'reject']:
            permission_classes = [permissions.IsAuthenticated, IsManagerPermission]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]

    def _user_can_act_on(self, user, leave_request) -> bool:
        """Check if the user is permitted to act on the given leave request.
        Managers can act on direct reports and department where they are Manager; HR/CEO/Admin can act per stage.
        """
        # Admin/superuser can always act
        if getattr(user, 'is_superuser', False) or getattr(user, 'role', None) == 'admin':
            return True
        role = getattr(user, 'role', None)
        if role == 'manager':
            # Can't act on own requests
            if leave_request.employee_id == getattr(user, 'id', None):
                return False
            return (
                leave_request.employee and (
                    leave_request.employee.manager_id == getattr(user, 'id', None)
                    or (
                        getattr(leave_request.employee, 'department_id', None)
                        and getattr(getattr(leave_request.employee, 'department', None), 'hod_id', None) == getattr(user, 'id', None)
                    )
                )
            )
        if role in ['hr', 'ceo']:
            # Defer to workflow service for stage/affiliate-specific checks
            try:
                from .services import ApprovalWorkflowService
                return ApprovalWorkflowService.can_user_approve(leave_request, user)
            except Exception:
                return False
        return False
    
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
            # HR sees:
            # - Merban: manager_approved (exclude SDSL/SBL)
            # - SDSL/SBL: ceo_approved (CEO already approved first)
            from django.db.models import Q
            merban_qs = self.get_queryset().filter(status='manager_approved').exclude(
                Q(employee__department__affiliate__name__in=['SDSL', 'SBL']) |
                Q(employee__affiliate__name__in=['SDSL', 'SBL'])
            )
            ceo_approved_qs = self.get_queryset().filter(status='ceo_approved')
            pending_requests = merban_qs.union(ceo_approved_qs)
        elif user_role == 'ceo':
            # CEO sees requests that require their approval - filtered by affiliate and workflow
            from .services import ApprovalWorkflowService
            # Standard (Merban): hr_approved; SDSL/SBL: pending
            candidate_qs = self.get_queryset().filter(status__in=['pending', 'hr_approved'])
            filtered_ids = []
            for req in candidate_qs:
                handler = ApprovalWorkflowService.get_handler(req)
                if handler.can_approve(user, req.status):
                    filtered_ids.append(req.id)
            pending_requests = self.get_queryset().filter(id__in=filtered_ids)
        elif user_role == 'admin':
            # Admin sees all not-final statuses (for troubleshooting)
            pending_requests = self.get_queryset().filter(status__in=['pending', 'manager_approved', 'hr_approved', 'ceo_approved'])
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

    @action(detail=False, methods=['get'])
    def ceo_approvals_categorized(self, request):
        """CEO-specific endpoint that categorizes pending requests by submitter role"""
        user = request.user
        user_role = getattr(user, 'role', None)
        
        if user_role != 'ceo' and not getattr(user, 'is_superuser', False):
            return Response({'detail': 'Only CEOs can access this endpoint'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Get all requests pending CEO approval
        pending_requests = self.get_queryset().filter(status='hr_approved')
        serializer = self.get_serializer(pending_requests, many=True)
        
        # Categorize by submitter role
        categorized = {
            'hod_manager': [],
            'hr': [],
            'staff': []
        }
        
        for request_data in serializer.data:
            # Get the employee role from the request
            submitter_role = request_data.get('employee_role', 'staff')
            
            if submitter_role == 'manager':
                categorized['hod_manager'].append(request_data)
            elif submitter_role == 'hr':
                categorized['hr'].append(request_data)
            else:
                categorized['staff'].append(request_data)
        
        response_data = {
            'categories': categorized,
            'total_count': len(serializer.data),
            'counts': {
                'hod_manager': len(categorized['hod_manager']),
                'hr': len(categorized['hr']),
                'staff': len(categorized['staff'])
            }
        }
        
        return Response(response_data)

    @action(detail=False, methods=['get'])
    def recent_activity(self, request):
        """Return the most recent requests the current approver acted on.

        - manager: requests they approved/rejected at manager stage
        - hr: requests they approved/rejected at HR stage
        - ceo: requests they approved/rejected at CEO stage
        - admin/superuser: treat as CEO

        Query param: limit (default 15)
        """
        user = request.user
        role = getattr(user, 'role', None)
        try:
            limit = int(request.query_params.get('limit', 15))
        except Exception:
            limit = 15

        # Build queryset based on role and action fields captured in model
        qs = LeaveRequest.objects.all()

        if getattr(user, 'is_superuser', False) or role == 'admin':
            # Treat admin like CEO for activity view
            acted_qs = qs.filter(ceo_approved_by=user).order_by('-ceo_approval_date', '-updated_at')
        elif role == 'ceo':
            acted_qs = qs.filter(ceo_approved_by=user).order_by('-ceo_approval_date', '-updated_at')
        elif role == 'hr':
            acted_qs = qs.filter(hr_approved_by=user).order_by('-hr_approval_date', '-updated_at')
        elif role == 'manager':
            acted_qs = qs.filter(manager_approved_by=user).order_by('-manager_approval_date', '-updated_at')
        else:
            acted_qs = qs.none()

        acted_qs = acted_qs[:limit]

        # Use list serializer for compact dashboard-friendly payload
        data = LeaveRequestListSerializer(acted_qs, many=True).data
        return Response({
            'count': len(data),
            'results': data,
        })
    
    @action(detail=True, methods=['get'])
    def trace(self, request, pk=None):
        """Debug endpoint: return approval state and next approver suggestions for a leave request."""
        from .services import ApprovalWorkflowService
        try:
            lr = LeaveRequest.objects.select_related('employee__department', 'employee__affiliate').get(pk=pk)
        except LeaveRequest.DoesNotExist:
            return Response({'error': 'LeaveRequest not found'}, status=status.HTTP_404_NOT_FOUND)

        handler = ApprovalWorkflowService.get_handler(lr)
        next_approver = ApprovalWorkflowService.get_next_approver(lr)

        data = {
            'id': lr.id,
            'employee': {
                'id': lr.employee.id,
                'name': lr.employee.get_full_name(),
                'affiliate': getattr(getattr(lr.employee, 'department', None), 'affiliate', None) and getattr(lr.employee.department.affiliate, 'name', None) or (getattr(lr.employee, 'affiliate', None) and getattr(lr.employee.affiliate, 'name', None)),
            },
            'status': lr.status,
            'current_approval_stage': lr.current_approval_stage,
            'manager_approved_by': lr.manager_approved_by and {'id': lr.manager_approved_by.id, 'name': lr.manager_approved_by.get_full_name(), 'email': lr.manager_approved_by.email} or None,
            'manager_approval_date': lr.manager_approval_date,
            'hr_approved_by': lr.hr_approved_by and {'id': lr.hr_approved_by.id, 'name': lr.hr_approved_by.get_full_name(), 'email': lr.hr_approved_by.email} or None,
            'hr_approval_date': lr.hr_approval_date,
            'ceo_approved_by': lr.ceo_approved_by and {'id': lr.ceo_approved_by.id, 'name': lr.ceo_approved_by.get_full_name(), 'email': lr.ceo_approved_by.email} or None,
            'ceo_approval_date': lr.ceo_approval_date,
            'next_approver_suggestion': next_approver and {'id': getattr(next_approver, 'id', None), 'name': getattr(next_approver, 'get_full_name', lambda: None)()} or None,
            'handler_class': handler.__class__.__name__,
        }

        # Add quick checks: can typical HR/CEO approve this now?
        User = get_user_model()
        hr_user = User.objects.filter(role='hr', is_active=True).first()
        ceo_user = User.objects.filter(role='ceo', is_active=True).first()
        data['can_hr_approve_now'] = bool(hr_user and ApprovalWorkflowService.can_user_approve(lr, hr_user))
        data['can_ceo_approve_now'] = bool(ceo_user and ApprovalWorkflowService.can_user_approve(lr, ceo_user))

        return Response(data)
    
    @action(detail=True, methods=['put'])
    def cancel(self, request, pk=None):
        """Cancel a leave request (only allowed by the requester while status is pending)"""
        import logging
        from notifications.services import LeaveNotificationService
        logger = logging.getLogger('leaves')
        
        try:
            # Use unrestricted lookup so HR/Admin can cancel on behalf of employees
            try:
                leave_request = LeaveRequest.objects.select_related('employee', 'leave_type').get(pk=pk)
            except LeaveRequest.DoesNotExist:
                return Response({'error': 'Leave request not found'}, status=status.HTTP_404_NOT_FOUND)
            user = request.user
            comments = request.data.get('comments', '')
            
            logger.info(f'Attempting to cancel leave request {pk} by user {user.username}')
            
            # Check if cancellation is allowed
            if not leave_request.can_be_cancelled(user):
                return Response({
                    'error': 'Cannot cancel this request. Only the requester can cancel their own pending request.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Cancel the request
            leave_request.cancel(user, comments)
            
            # Send notification
            LeaveNotificationService.notify_leave_cancelled(leave_request, user)
            
            # Update leave balance
            self._update_leave_balance(leave_request, 'cancel')
            
            logger.info(f'Leave request {pk} cancelled by {user.username}')
            return Response({
                'message': 'Leave request cancelled successfully',
                'status': leave_request.status
            })
            
        except Exception as e:
            logger.error(f'Error cancelling leave request {pk}: {str(e)}', exc_info=True)
            return Response({'error': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['put'])
    def approve(self, request, pk=None):
        """Multi-stage approval system with affiliate-based routing"""
        import logging
        from notifications.services import LeaveNotificationService
        from .services import ApprovalWorkflowService
        logger = logging.getLogger('leaves')
        
        try:
            leave_request = self.get_object()
            user = request.user
            comments = request.data.get('approval_comments', '')
            
            logger.info(f'Attempting to approve leave request {pk} by user {user.username} (role: {getattr(user, "role", "unknown")})')
            
            # Authorization: ensure user can act on this request
            if not self._user_can_act_on(user, leave_request):
                return Response({'error': 'You are not allowed to act on this request'}, status=status.HTTP_403_FORBIDDEN)

            # Check if request can be approved
            if leave_request.status == 'rejected':
                return Response({'error': 'Cannot approve a rejected request'}, status=status.HTTP_400_BAD_REQUEST)
            elif leave_request.status == 'approved':
                return Response({'error': 'Request is already fully approved'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Use new workflow service for approval
            try:
                ApprovalWorkflowService.approve_request(leave_request, user, comments)
                
                # Send appropriate notifications
                if leave_request.status == 'manager_approved':
                    LeaveNotificationService.notify_manager_approval(leave_request, user)
                    message = 'Leave request approved by manager'
                elif leave_request.status == 'hr_approved':
                    LeaveNotificationService.notify_hr_approval(leave_request, user)
                    message = 'Leave request approved by HR'
                elif leave_request.status == 'approved':
                    LeaveNotificationService.notify_ceo_approval(leave_request, user)
                    # Update leave balance only on final approval
                    self._update_leave_balance(leave_request, 'approve')
                    message = 'Leave request given final approval'
                else:
                    message = 'Leave request approved'
                
                logger.info(f'Leave request {pk} approved by {user.username}, new status: {leave_request.status}')
                
            except ValueError as ve:
                logger.warning(f'Approval validation failed for request {pk}: {str(ve)}')
                return Response({'error': str(ve)}, status=status.HTTP_403_FORBIDDEN)
            
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
            
            # Authorization: ensure user can act on this request
            if not self._user_can_act_on(user, leave_request):
                return Response({'error': 'You are not allowed to act on this request'}, status=status.HTTP_403_FORBIDDEN)

            if leave_request.status in ['rejected', 'cancelled']:
                return Response({'error': 'Request is already rejected or cancelled'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Determine rejection stage based on user role and current status
            user_role = getattr(user, 'role', None)
            rejection_stage = None
            
            if user_role == 'manager' and leave_request.status == 'pending':
                rejection_stage = 'manager'
            elif user_role == 'hr' and leave_request.status in ['pending', 'manager_approved', 'ceo_approved']:
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

    @action(detail=False, methods=['get'])
    def approval_counts(self, request):
        """Get counts of pending approvals for the current user's role"""
        import logging
        logger = logging.getLogger('leaves')
        user = request.user
        user_role = getattr(user, 'role', None)
        try:
            logger.info(f"approval_counts called by user={getattr(user, 'username', None)} role={user_role} path={request.path}")
        except Exception:
            logger.exception('Failed to log approval_counts call')
        
        counts = {
            'manager_approvals': 0,
            'hr_approvals': 0, 
            'ceo_approvals': 0,
            'total': 0
        }
        try:
            if user_role == 'manager':
                counts['manager_approvals'] = self.get_queryset().filter(status='pending').count()
            elif user_role == 'hr':
                # HR: Merban manager_approved + SDSL/SBL ceo_approved
                from django.db.models import Q
                merban_count = self.get_queryset().filter(status='manager_approved').exclude(
                    Q(employee__department__affiliate__name__in=['SDSL', 'SBL']) |
                    Q(employee__affiliate__name__in=['SDSL', 'SBL'])
                ).count()
                ceo_approved_count = self.get_queryset().filter(status='ceo_approved').count()
                counts['hr_approvals'] = merban_count + ceo_approved_count
            elif user_role == 'ceo':
                # Use same logic as pending_approvals endpoint
                from .services import ApprovalWorkflowService
                ceo_count = 0
                candidate_qs = self.get_queryset().filter(status__in=['pending', 'hr_approved'])
                for req in candidate_qs:
                    handler = ApprovalWorkflowService.get_handler(req)
                    if handler.can_approve(user, req.status):
                        ceo_count += 1
                counts['ceo_approvals'] = ceo_count
            elif user_role == 'admin':
                counts['manager_approvals'] = self.get_queryset().filter(status='pending').count()
                counts['hr_approvals'] = self.get_queryset().filter(status__in=['manager_approved', 'ceo_approved']).count()
                counts['ceo_approvals'] = self.get_queryset().filter(status='hr_approved').count()

            counts['total'] = counts['manager_approvals'] + counts['hr_approvals'] + counts['ceo_approvals']

        except Exception as e:
            logger.error(f'Error computing approval_counts for user={getattr(user, "username", None)}: {str(e)}', exc_info=True)
            # Return zeros (safe default) and a debug message so the frontend can display gracefully
            return Response({**counts, 'error': 'unable to compute counts'})

        return Response(counts)

    @action(detail=False, methods=['post'], url_path='system_reset')
    def system_reset(self, request):
        """
        Admin-only feature to reset all leave requests and balances for testing.
        WARNING: This will delete ALL leave requests and reset ALL leave balances!
        """
        user = request.user
        
        # Only allow admin/superuser access
        if not (getattr(user, 'is_superuser', False) or getattr(user, 'role', None) == 'admin'):
            return Response({'error': 'Only administrators can perform system reset'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Require confirmation parameter
        # Accept multiple names for compatibility with older frontend requests
        confirm_raw = (request.data.get('confirm_reset') or request.data.get('confirmation') or request.data.get('confirm') or '')
        confirm = str(confirm_raw).strip().lower()
        import logging
        logger = logging.getLogger('leaves')
        logger.info(f'system_reset called by {getattr(user, "username", None)}; received_confirmation={confirm_raw}')

        if confirm != 'yes, reset everything':
            return Response({
                'error': 'System reset requires confirmation',
                'required_confirmation': 'yes, reset everything',
                'received': confirm_raw
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from django.db import transaction
            # Count records before deletion and perform deletion inside a transaction
            with transaction.atomic():
                leave_requests_count = LeaveRequest.objects.count()
                balances_count = LeaveBalance.objects.count()

                LeaveRequest.objects.all().delete()
                # Reset all leave balances to default state (keep entitled_days)
                LeaveBalance.objects.all().update(used_days=0, pending_days=0)

            logger.info(f'System reset performed by {user.username}: {leave_requests_count} requests deleted, {balances_count} balances reset')

            return Response({
                'message': 'System reset completed successfully',
                'deleted_requests': leave_requests_count,
                'reset_balances': balances_count,
                'performed_by': user.get_full_name() or user.username,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger('leaves')
            logger.error(f'Error during system reset by {user.username}: {str(e)}', exc_info=True)
            return Response({
                'error': f'System reset failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
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
