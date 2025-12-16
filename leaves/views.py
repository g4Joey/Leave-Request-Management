from django.shortcuts import render
from typing import Any
import logging

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import LeaveRequest, LeaveType, LeaveBalance, LeaveGradeEntitlement, LeaveInterruptRequest, LeaveInterruptLog, LeaveResumeEvent
from .serializers import (
    LeaveRequestSerializer, 
    LeaveRequestListSerializer,
    LeaveApprovalSerializer,
    LeaveTypeSerializer, 
    LeaveBalanceSerializer,
    LeaveInterruptRequestSerializer,
    LeaveResumeEventSerializer,
    EmploymentGradeSerializer,
    LeaveGradeEntitlementSerializer,
    _build_timeline_events,
)
from users.models import EmploymentGrade
from .grade_entitlements import apply_grade_entitlements
from .services import ApprovalRoutingService


def _perform_cancel_action(leave_request, user, comments, balance_updater):
    """Shared cancel helper used by both request and manager viewsets.

    Returns a tuple of (success: bool, status_code: int, message: str).
    """
    logger = logging.getLogger('leaves')

    if not hasattr(leave_request, 'can_be_cancelled') or not leave_request.can_be_cancelled(user):
        return False, status.HTTP_403_FORBIDDEN, 'Cannot cancel this request. Only the requester can cancel their own pending request.'

    try:
        leave_request.cancel(user, comments)
    except ValidationError as ve:
        message = '; '.join(ve.messages) if hasattr(ve, 'messages') else str(ve)
        return False, status.HTTP_400_BAD_REQUEST, message or 'Unable to cancel this request.'
    except Exception:
        logger.error('Unexpected error while cancelling leave request', exc_info=True)
        return False, status.HTTP_500_INTERNAL_SERVER_ERROR, 'Unable to cancel this request right now.'

    # Notify interested parties; failure is non-fatal.
    try:
        from notifications.services import LeaveNotificationService
        LeaveNotificationService.notify_leave_cancelled(leave_request, user)
    except Exception:
        logger.warning('Failed to send cancellation notification', exc_info=True)

    # Update balance; failure is non-fatal but logged.
    try:
        balance_updater(leave_request, 'cancel')
    except Exception:
        logger.warning('Failed to update balance after cancellation', exc_info=True)

    return True, status.HTTP_200_OK, ''


class LeaveTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for leave types.
    Read access is available to authenticated users (active types only for non-HR).
    HR users may create, update or delete leave types and perform HR-only actions.
    """
    queryset = LeaveType.objects.filter(is_active=True)
    serializer_class = LeaveTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):  # type: ignore[override]
        """Return all leave types for HR, only active for others"""
        if self._is_hr(self.request):
            return LeaveType.objects.all()
        return LeaveType.objects.filter(is_active=True)

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

    def create(self, request, *args, **kwargs):
        if not self._is_hr(request):
            return Response({'detail': 'Only HR can create leave types'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not self._is_hr(request):
            return Response({'detail': 'Only HR can update leave types'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not self._is_hr(request):
            return Response({'detail': 'Only HR can update leave types'}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not self._is_hr(request):
            return Response({'detail': 'Only HR can delete leave types'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

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

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """HR-only: Activate a leave type"""
        if not self._is_hr(request):
            return Response({'detail': 'Only HR can activate leave types'}, status=status.HTTP_403_FORBIDDEN)

        leave_type = self.get_object()
        if leave_type.is_active:
            return Response({'detail': 'Leave type is already active'}, status=status.HTTP_400_BAD_REQUEST)
        
        leave_type.is_active = True
        leave_type.save(update_fields=['is_active'])
        
        return Response({
            'message': f'{leave_type.name} has been activated',
            'leave_type': LeaveTypeSerializer(leave_type).data
        })

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """HR-only: Deactivate a leave type"""
        if not self._is_hr(request):
            return Response({'detail': 'Only HR can deactivate leave types'}, status=status.HTTP_403_FORBIDDEN)

        leave_type = self.get_object()
        if not leave_type.is_active:
            return Response({'detail': 'Leave type is already inactive'}, status=status.HTTP_400_BAD_REQUEST)
        
        leave_type.is_active = False
        leave_type.save(update_fields=['is_active'])
        
        return Response({
            'message': f'{leave_type.name} has been deactivated',
            'leave_type': LeaveTypeSerializer(leave_type).data
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

    # Helpers for combined feeds
    def _final_approver_event(self, lr: LeaveRequest):
        """Pick the final approver event respecting affiliate rules.

        Merban: CEO/final; SDSL/SBL: HR/final.
        """
        aff = None
        try:
            aff = (getattr(getattr(lr.employee, 'department', None), 'affiliate', None) or getattr(lr.employee, 'affiliate', None))
            aff = getattr(aff, 'name', None)
        except Exception:
            aff = None
        aff_up = (aff or '').upper()

        preferred = ['ceo', 'hr'] if aff_up in ['', 'MERBAN', 'MERBAN CAPITAL'] else ['hr', 'ceo']

        candidates = []
        if lr.manager_approval_date:
            candidates.append({'role': 'manager', 'timestamp': lr.manager_approval_date, 'label': 'Manager approved'})
        if lr.hr_approval_date:
            candidates.append({'role': 'hr', 'timestamp': lr.hr_approval_date, 'label': 'HR approved'})
        if lr.ceo_approval_date:
            candidates.append({'role': 'ceo', 'timestamp': lr.ceo_approval_date, 'label': 'CEO approved'})
        if lr.approval_date:
            candidates.append({'role': 'final', 'timestamp': lr.approval_date, 'label': 'Approved'})

        if not candidates:
            return None

        for pref in preferred:
            for c in candidates:
                if c['role'] == pref:
                    return c

        return max(candidates, key=lambda c: c['timestamp'])

    def _build_leave_entry(self, lr: LeaveRequest, viewer):
        final_ev = self._final_approver_event(lr)
        timeline = _build_timeline_events(lr, viewer)
        interruption = None
        if lr.interruption_note and lr.interrupted_at:
            interruption = {
                'note': lr.interruption_note,
                'timestamp': lr.interrupted_at,
            }
        try:
            affiliate = (getattr(getattr(lr.employee, 'department', None), 'affiliate', None) or getattr(lr.employee, 'affiliate', None))
            affiliate_name = getattr(affiliate, 'name', None)
        except Exception:
            affiliate_name = None

        # Check for pending recall requests
        has_pending_recall = LeaveInterruptRequest.objects.filter(
            leave_request=lr,
            type='manager_recall',
            status='pending_staff'
        ).exists()

        # Check if user can cancel this request
        can_cancel = False
        try:
            can_cancel = lr.can_be_cancelled(viewer)
        except Exception:
            pass

        # Compute request number for this user (chronological order)
        request_number = None
        try:
            # Count how many requests this user made before this one (inclusive)
            request_number = LeaveRequest.objects.filter(
                employee=lr.employee,
                created_at__lte=lr.created_at
            ).count()
        except Exception:
            pass

        return {
            'record_type': 'leave',
            'id': lr.id,
            'request_number': request_number,
            'leave_type_name': getattr(lr.leave_type, 'name', ''),
            'start_date': lr.start_date,
            'end_date': lr.end_date,
            'total_days': lr.total_days,
            'working_days': lr.working_days,
            'reason': lr.reason or '',
            'status': lr.status,
            'status_display': lr.get_dynamic_status_display(),
            'stage_label': getattr(lr, 'stage_label', None) or None,
            'approval_date': lr.approval_date,
            'manager_approval_date': lr.manager_approval_date,
            'hr_approval_date': lr.hr_approval_date,
            'ceo_approval_date': lr.ceo_approval_date,
            'final_event': final_ev,
            'interruption': interruption,
            'interruption_credited_days': lr.interruption_credited_days or 0,
            'actual_resume_date': lr.actual_resume_date,
            'timeline_events': timeline,
            'employee_department_affiliate': affiliate_name,
            'has_pending_recall': has_pending_recall,
            'can_cancel': can_cancel,
            'created_at': lr.created_at,
            'sort_ts': lr.updated_at or lr.created_at,
        }

    def _build_interrupt_entry(self, ir: LeaveInterruptRequest, viewer):
        lr = ir.leave_request

        def status_display():
            mapping = {
                'pending_manager': 'Pending Manager Approval',
                'pending_hr': 'Pending HR Approval',
                'pending_ceo': 'Pending CEO Approval',
                'pending_staff': 'Pending Staff Response',
                'approved': 'Approved',
                'rejected': 'Rejected',
                'applied': 'Applied'
            }
            return mapping.get(ir.status, ir.status)

        def pending_with():
            if ir.status == 'pending_manager':
                return 'Manager'
            if ir.status == 'pending_hr':
                return 'HR'
            if ir.status == 'pending_ceo':
                return 'CEO'
            if ir.status == 'pending_staff':
                return 'Staff'
            return None

        type_label = 'Recall Request' if ir.type == 'manager_recall' else 'Early Return Request'

        try:
            affiliate = (getattr(getattr(lr.employee, 'department', None), 'affiliate', None) or getattr(lr.employee, 'affiliate', None))
            affiliate_name = getattr(affiliate, 'name', None)
        except Exception:
            affiliate_name = None

        # Compute linked leave request number
        leave_request_number = None
        if lr:
            try:
                leave_request_number = LeaveRequest.objects.filter(
                    employee=lr.employee,
                    created_at__lte=lr.created_at
                ).count()
            except Exception:
                pass

        return {
            'record_type': 'interrupt',
            'id': ir.id,
            'interrupt_type': ir.type,
            'type_label': type_label,
            'status': ir.status,
            'status_display': status_display(),
            'pending_with': pending_with(),
            'requested_resume_date': ir.requested_resume_date,
            'reason': ir.reason,
            'leave_request_id': lr.id if lr else None,
            'leave_request_number': leave_request_number,
            'leave_type_name': getattr(getattr(lr, 'leave_type', None), 'name', None),
            'start_date': getattr(lr, 'start_date', None),
            'end_date': getattr(lr, 'end_date', None),
            'total_days': getattr(lr, 'total_days', None),
            'working_days': getattr(lr, 'working_days', None),
            'employee_department_affiliate': affiliate_name,
            'sort_ts': ir.updated_at or ir.created_at,
        }

    def _calculate_credited_working_days(self, resume_date, end_date):
        """Inclusive working days from resume_date to end_date (resuming on resume_date)."""
        from datetime import timedelta
        days = 0
        current = resume_date
        while current <= end_date:
            if current.weekday() < 5:
                days += 1
            current += timedelta(days=1)
        return days

    def _apply_interrupt(self, leave_request: LeaveRequest, interrupt: LeaveInterruptRequest, actor):
        """Apply an approved interruption: credit back days, log, and update balances."""
        from django.utils import timezone
        credited = self._calculate_credited_working_days(interrupt.requested_resume_date, leave_request.end_date)
        interrupt.status = 'approved'
        interrupt.credited_working_days = credited
        interrupt.applied_at = timezone.now()
        interrupt.save(update_fields=['status', 'credited_working_days', 'applied_at', 'updated_at'])

        # Tag the leave with interruption info for auditing (do not alter original dates)
        note_prefix = 'Recalled on' if interrupt.type == 'manager_recall' else 'Early return on'
        leave_request.interruption_credited_days = credited
        leave_request.interruption_note = f"{note_prefix} {interrupt.requested_resume_date} — {credited} days credited. Reason: {interrupt.reason}"
        leave_request.interrupted_at = interrupt.applied_at
        leave_request.interrupted_by = actor
        leave_request.save(update_fields=['interruption_credited_days', 'interruption_note', 'interrupted_at', 'interrupted_by', 'updated_at'])

        # Recalculate balance for that leave type/year
        try:
            balance = LeaveBalance.objects.filter(employee=leave_request.employee, leave_type=leave_request.leave_type, year=leave_request.start_date.year).first()
            if balance:
                balance.update_balance()
        except Exception:
            pass

        LeaveInterruptLog.objects.create(
            leave_request=leave_request,
            interrupt_request=interrupt,
            actor=actor,
            event='applied',
            credited_days=credited,
            comment=interrupt.reason or ''
        )

        # Optional: notify parties (non-fatal)
        try:
            from notifications.services import LeaveNotificationService
            LeaveNotificationService.notify_leave_cancelled(leave_request, actor)  # reuse notification channel for visibility
        except Exception:
            pass
    
    def get_queryset(self):  # type: ignore[override]
        """Return appropriate queryset.

        For approval / oversight actions we need visibility across employees, not just the
        requesting user's own leave requests. Previous implementation restricted all actions
        which caused HR/CEO pages to miss items and permission errors (CEO approving others).
        """
        # Actions that require cross-employee visibility
        cross_actions = {
            'pending_approvals', 'hr_approvals_categorized', 'ceo_approvals_categorized',
            'recent_activity', 'approve', 'reject', 'approval_counts'
        }
        user = getattr(self.request, 'user', None)
        
        # Only provide cross-employee visibility for specific approval/oversight actions
        if self.action in cross_actions:
            return LeaveRequest.objects.select_related('employee', 'employee__department', 'employee__department__affiliate', 'employee__affiliate')
        
        # For all other actions (history, list, dashboard), show only the user's own requests
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
            
            # Stage initialization rules on creation:
            # - Default: keep status='pending' and let ApprovalWorkflowService drive stages
            # - Merban staff with no manager/HOD assigned: skip manager stage (set to manager_approved)
            # - Do NOT auto-set HR-approved for HR users; HR should approve (self-approve allowed) via Approvals page
            user_role = getattr(user, 'role', None)
            has_manager = hasattr(user, 'manager') and user.manager is not None

            # Determine affiliate to decide whether to skip manager when no manager exists
            try:
                from .services import ApprovalRoutingService
                affiliate_name = ApprovalRoutingService.get_employee_affiliate_name(user)
            except Exception:
                affiliate_name = 'DEFAULT'

            # Refined skip logic:
            # Only skip manager stage if requester is manager/hod/hr OR truly lacks both a direct manager and a department HOD.
            # Staff with a department HOD but no direct manager should still start at 'pending'.
            try:
                dept_hod = getattr(getattr(user, 'department', None), 'hod', None)
            except Exception:
                dept_hod = None
            # Skip / escalate logic:
            # - Manager or HOD requester: skip manager stage (move to manager_approved)
            # - HR requester (Merban): start at manager_approved so HR can act (self-approval)
            # - HR requester (SDSL/SBL CEO-first flow): start at ceo_approved so HR finalizes directly
            # - SDSL/SBL CEO requester: route directly to HR (status=ceo_approved) and label Pending HR
            # - Staff with neither manager nor HOD (Merban only): escalate to manager_approved
            if user_role in ['manager', 'hod']:
                serializer.validated_data['status'] = 'manager_approved'
            elif user_role == 'hr':
                if affiliate_name in ['SDSL', 'SBL']:
                    serializer.validated_data['status'] = 'ceo_approved'
                else:
                    serializer.validated_data['status'] = 'manager_approved'
            elif user_role == 'ceo' and affiliate_name in ['SDSL', 'SBL']:
                serializer.validated_data['status'] = 'ceo_approved'
            else:
                if not has_manager and not dept_hod and affiliate_name not in ['SDSL', 'SBL']:
                    serializer.validated_data['status'] = 'manager_approved'
                    logger.info(f'Staff {user.username} has neither manager nor HOD; auto-escalating to HR stage.')
            
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
    def history_combined(self, request):
        """Return leave history plus interrupt requests as separate entries for the current user."""
        user = request.user
        viewer = user
        leaves_qs = self.get_queryset().select_related('leave_type', 'employee__department__affiliate', 'employee__affiliate')
        interrupts_qs = LeaveInterruptRequest.objects.filter(leave_request__employee=user).select_related('leave_request__leave_type', 'leave_request__employee__department__affiliate', 'leave_request__employee__affiliate')

        entries = [self._build_leave_entry(lr, viewer) for lr in leaves_qs]
        entries += [self._build_interrupt_entry(ir, viewer) for ir in interrupts_qs]
        entries = sorted(entries, key=lambda e: e.get('sort_ts') or timezone.now(), reverse=True)
        return Response(entries)
    
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
                if item.get('stage_label') and item.get('status') in ['pending', 'manager_approved', 'hr_approved', 'ceo_approved']:
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

    @action(detail=False, methods=['get'])
    def recent_combined(self, request):
        """Latest leave requests and interrupt requests for the current user (combined feed)."""
        user = request.user
        viewer = user
        try:
            limit = int(request.query_params.get('limit', 5))
        except Exception:
            limit = 5

        leaves_qs = self.get_queryset().select_related('leave_type', 'employee__department__affiliate', 'employee__affiliate').order_by('-updated_at')[: limit * 3]
        interrupts_qs = LeaveInterruptRequest.objects.filter(leave_request__employee=user).select_related('leave_request__leave_type', 'leave_request__employee__department__affiliate', 'leave_request__employee__affiliate').order_by('-updated_at')[: limit * 3]

        entries = [self._build_leave_entry(lr, viewer) for lr in leaves_qs]
        entries += [self._build_interrupt_entry(ir, viewer) for ir in interrupts_qs]
        entries = sorted(entries, key=lambda e: e.get('sort_ts') or timezone.now(), reverse=True)
        return Response(entries[:limit])

    def _normalize_role(self, role: str) -> str:
        if not role:
            return ''
        r = role.lower()
        if r in ['hod']:
            return 'manager'
        if r in ['employee', 'staff']:
            return 'junior_staff'
        return r

    def _determine_early_return_initial_status(self, leave: LeaveRequest, actor) -> str:
        """Return the initial interrupt status based on affiliate and requester role."""
        aff = ApprovalRoutingService.get_employee_affiliate_name(getattr(leave, 'employee', None))
        role = self._normalize_role(getattr(actor, 'role', ''))

        # SDSL/SBL: CEO first, HR final. CEO self-requests go straight to HR.
        if aff in ['SDSL', 'SBL']:
            if role == 'ceo':
                return 'pending_hr'
            return 'pending_ceo'

        # Merban/default: staff -> manager -> HR; managers -> HR; HR -> CEO.
        if role in ['manager']:
            return 'pending_hr'
        if role == 'hr':
            return 'pending_ceo'
        # Default staff path
        return 'pending_manager'

    @action(detail=True, methods=['post'])
    def return_early(self, request, pk=None):
        """Staff-initiated early return (requires manager then HR approval)."""
        leave = self.get_object()
        user = request.user
        if user != leave.employee:
            return Response({'detail': 'Only the requester can initiate early return.'}, status=status.HTTP_403_FORBIDDEN)
        if leave.status != 'approved':
            return Response({'detail': 'Early return is only available for fully approved requests.'}, status=status.HTTP_400_BAD_REQUEST)

        resume_date_raw = request.data.get('resume_date')
        reason = request.data.get('reason', '')
        if not resume_date_raw:
            return Response({'detail': 'resume_date is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from datetime import date
            resume_date = date.fromisoformat(resume_date_raw)
        except Exception:
            return Response({'detail': 'Invalid resume_date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        if resume_date < leave.start_date or resume_date > leave.end_date:
            return Response({'detail': 'Resume date must be between start_date and end_date.'}, status=status.HTTP_400_BAD_REQUEST)

        credited = self._calculate_credited_working_days(resume_date, leave.end_date)
        if credited <= 0:
            return Response({'detail': 'No working days remain to credit.'}, status=status.HTTP_400_BAD_REQUEST)

        initial_status = self._determine_early_return_initial_status(leave, user)
        if not initial_status:
            return Response({'detail': 'Early return not allowed for this role/affiliate.'}, status=status.HTTP_403_FORBIDDEN)

        interrupt = LeaveInterruptRequest.objects.create(
            leave_request=leave,
            type='staff_return',
            status=initial_status,
            requested_resume_date=resume_date,
            reason=reason,
            initiated_by=user,
            initiated_role=getattr(user, 'role', '')
        )
        LeaveInterruptLog.objects.create(
            leave_request=leave,
            interrupt_request=interrupt,
            actor=user,
            event='requested',
            comment=reason,
            credited_days=credited
        )
        return Response(LeaveInterruptRequestSerializer(interrupt).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def accept_recall(self, request, pk=None):
        """Staff accepts manager recall and apply credit immediately."""
        leave = self.get_object()
        user = request.user
        pending = LeaveInterruptRequest.objects.filter(leave_request=leave, type='manager_recall', status='pending_staff').first()
        if not pending:
            return Response({'detail': 'No pending recall to accept.'}, status=status.HTTP_400_BAD_REQUEST)
        if user != leave.employee:
            return Response({'detail': 'Only the staff can accept this recall.'}, status=status.HTTP_403_FORBIDDEN)

        pending.status = 'approved'
        pending.staff_decision_by = user
        pending.staff_decision_at = timezone.now()
        pending.staff_decision_comment = request.data.get('reason', '')
        pending.save(update_fields=['status', 'staff_decision_by', 'staff_decision_at', 'staff_decision_comment', 'updated_at'])
        self._apply_interrupt(leave, pending, user)
        LeaveInterruptLog.objects.create(leave_request=leave, interrupt_request=pending, actor=user, event='staff_accepted', comment=pending.staff_decision_comment, credited_days=pending.credited_working_days)
        return Response({'detail': 'Recall accepted and days credited.', 'credited_days': pending.credited_working_days})

    @action(detail=True, methods=['post'])
    def reject_recall(self, request, pk=None):
        """Staff rejects manager recall."""
        leave = self.get_object()
        user = request.user
        pending = LeaveInterruptRequest.objects.filter(leave_request=leave, type='manager_recall', status='pending_staff').first()
        if not pending:
            return Response({'detail': 'No pending recall to reject.'}, status=status.HTTP_400_BAD_REQUEST)
        if user != leave.employee:
            return Response({'detail': 'Only the staff can reject this recall.'}, status=status.HTTP_403_FORBIDDEN)
        pending.status = 'rejected'
        pending.staff_decision_by = user
        pending.staff_decision_at = timezone.now()
        pending.staff_decision_comment = request.data.get('reason', '')
        pending.save(update_fields=['status', 'staff_decision_by', 'staff_decision_at', 'staff_decision_comment', 'updated_at'])
        LeaveInterruptLog.objects.create(leave_request=leave, interrupt_request=pending, actor=user, event='staff_rejected', comment=pending.staff_decision_comment)
        # Tag the leave so history shows the rejection event
        try:
            leave.interruption_note = f"Recall rejected on {pending.staff_decision_at.date()} — {pending.staff_decision_comment}".strip()
            leave.interrupted_at = pending.staff_decision_at
            leave.interrupted_by = user
            leave.save(update_fields=['interruption_note', 'interrupted_at', 'interrupted_by', 'updated_at'])
        except Exception:
            pass
        return Response({'detail': 'Recall rejected.'})

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Record actual resume date (only on/after end_date)."""
        leave = self.get_object()
        user = request.user
        if user != leave.employee:
            return Response({'detail': 'Only the requester can record resume.'}, status=status.HTTP_403_FORBIDDEN)
        resume_date_raw = request.data.get('resume_date')
        if not resume_date_raw:
            return Response({'detail': 'resume_date is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from datetime import date
            resume_date = date.fromisoformat(resume_date_raw)
        except Exception:
            return Response({'detail': 'Invalid resume_date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        if resume_date < leave.end_date:
            return Response({'detail': 'Resume date cannot be before leave end date.'}, status=status.HTTP_400_BAD_REQUEST)
        LeaveResumeEvent.objects.create(leave_request=leave, resume_date=resume_date, recorded_by=user)
        leave.actual_resume_date = resume_date
        leave.save(update_fields=['actual_resume_date', 'updated_at'])
        return Response({'detail': 'Resume recorded.', 'resume_date': resume_date})


class ManagerLeaveViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Managers to view and approve leave requests - supports R4
    Note: Despite being ModelViewSet, actual create/update/delete are not exposed.
    Only custom actions (approve, reject, etc.) perform writes.
    """
    serializer_class = LeaveRequestListSerializer  # Use list serializer with employee_department, employee_role, etc.
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        'status', 'leave_type', 'start_date', 'end_date', 'employee',
        'total_days', 'actual_resume_date', 'interrupted_at'
    ]
    search_fields = [
        'employee__first_name', 'employee__last_name', 'employee__email',
        'reason', 'leave_type__name',
        'start_date', 'end_date', 'actual_resume_date', 'interrupted_at',
        'manager_approval_date', 'hr_approval_date', 'ceo_approval_date'
    ]
    ordering_fields = ['created_at', 'start_date', 'end_date']
    ordering = ['-created_at']

    def _calculate_credited_working_days(self, resume_date, end_date):
        from datetime import timedelta
        days = 0
        current = resume_date
        while current <= end_date:
            if current.weekday() < 5:
                days += 1
            current += timedelta(days=1)
        return days

    def _apply_interrupt(self, leave_request: LeaveRequest, interrupt: LeaveInterruptRequest, actor):
        """Apply an approved interruption: credit back days, log, and update balances."""
        from django.utils import timezone
        credited = self._calculate_credited_working_days(interrupt.requested_resume_date, leave_request.end_date)
        interrupt.status = 'approved'
        interrupt.credited_working_days = credited
        interrupt.applied_at = timezone.now()
        interrupt.save(update_fields=['status', 'credited_working_days', 'applied_at', 'updated_at'])

        note_prefix = 'Recalled on' if interrupt.type == 'manager_recall' else 'Early return on'
        leave_request.interruption_credited_days = credited
        leave_request.interruption_note = f"{note_prefix} {interrupt.requested_resume_date} — {credited} days credited. Reason: {interrupt.reason}"
        leave_request.interrupted_at = interrupt.applied_at
        leave_request.interrupted_by = actor
        leave_request.save(update_fields=['interruption_credited_days', 'interruption_note', 'interrupted_at', 'interrupted_by', 'updated_at'])

        try:
            balance = LeaveBalance.objects.filter(employee=leave_request.employee, leave_type=leave_request.leave_type, year=leave_request.start_date.year).first()
            if balance:
                balance.update_balance()
        except Exception:
            pass

        LeaveInterruptLog.objects.create(
            leave_request=leave_request,
            interrupt_request=interrupt,
            actor=actor,
            event='applied',
            credited_days=credited,
            comment=interrupt.reason or ''
        )

        try:
            from notifications.services import LeaveNotificationService
            LeaveNotificationService.notify_leave_cancelled(leave_request, actor)
        except Exception:
            pass
    # Allow POST for recall and interrupt approvals.
    http_method_names = ['get', 'put', 'post', 'head', 'options']  # Disable DELETE, PATCH
    
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
        qs = LeaveRequest.objects.select_related(
            'employee', 
            'employee__affiliate', 
            'employee__department', 
            'employee__department__affiliate'
        )
        role = getattr(user, 'role', None)

        # Superuser/admin: full access
        if getattr(user, 'is_superuser', False) or role == 'admin':
            return qs

        if role == 'manager':
            # Direct reports or same department where user is HOD/Manager, but EXCLUDE own requests
            return qs.filter(Q(employee__manager=user) | Q(employee__department__hod=user)).exclude(employee=user)

        if role == 'hr':
            # Items that have passed Manager stage or are pending (to allow visibility)
            # Include 'ceo_approved' for SDSL/SBL CEO-first flow where HR gives final approval
            return qs.filter(status__in=['pending', 'manager_approved', 'hr_approved', 'ceo_approved', 'approved', 'rejected'])

        if role == 'ceo':
            # Items that require or have passed CEO stage.
            # Merban: hr_approved; SDSL/SBL: pending. Include approved/rejected for record views.
            return qs.filter(status__in=['pending', 'hr_approved', 'approved', 'rejected'])

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

    def _normalize_role(self, role: str) -> str:
        if not role:
            return ''
        r = role.lower()
        if r == 'hod':
            return 'manager'
        if r in ['employee', 'staff']:
            return 'junior_staff'
        return r

    def _same_affiliate(self, a, b) -> bool:
        def aff_id(u):
            try:
                if getattr(u, 'affiliate', None):
                    return getattr(u.affiliate, 'id', None)
                if getattr(u, 'department', None) and getattr(u.department, 'affiliate', None):
                    return getattr(u.department.affiliate, 'id', None)
            except Exception:
                return None
            return None
        return aff_id(a) is not None and aff_id(a) == aff_id(b)

    def _can_initiate_recall(self, actor, leave_request) -> bool:
        """Enforce recall initiator rules across affiliates and roles."""
        if getattr(actor, 'is_superuser', False) or getattr(actor, 'role', None) == 'admin':
            return True

        actor_role = self._normalize_role(getattr(actor, 'role', ''))
        target_role = self._normalize_role(getattr(getattr(leave_request, 'employee', None), 'role', ''))
        aff = ApprovalRoutingService.get_employee_affiliate_name(getattr(leave_request, 'employee', None))

        # SDSL/SBL: affiliate CEO can recall affiliate staff; managers can recall direct reports.
        if aff in ['SDSL', 'SBL']:
            if actor_role == 'ceo' and self._same_affiliate(actor, getattr(leave_request, 'employee', None)):
                return target_role in ['junior_staff', 'senior_staff', 'manager']
            if actor_role == 'manager':
                return self._user_can_act_on(actor, leave_request)
            return False

        # Merban/default rules
        if target_role in ['junior_staff', 'senior_staff']:
            return actor_role == 'manager' and self._user_can_act_on(actor, leave_request)
        if target_role in ['manager']:
            return actor_role in ['hr', 'ceo']
        if target_role == 'hr':
            return actor_role == 'ceo'
        return False

    def _update_leave_balance(self, leave_request, action):
        """Update leave balance based on approval/rejection/cancellation.

        This mirrors the helper implemented on the request-level viewset so
        manager-facing actions can call the same behavior without causing
        an AttributeError when invoked from `ManagerLeaveViewSet`.
        """
        import logging
        logger = logging.getLogger('leaves')

        try:
            logger.info(f'Updating leave balance for {action} action on request {getattr(leave_request, "id", "?" )}')
            balance = LeaveBalance.objects.get(
                employee=leave_request.employee,
                leave_type=leave_request.leave_type,
                year=leave_request.start_date.year
            )

            logger.info(f'Found balance for {getattr(leave_request.employee, "username", "?")} - {getattr(leave_request.leave_type, "name", "?")} - {leave_request.start_date.year}')

            # Recompute from source of truth to avoid negative values
            balance.update_balance()
            logger.info(f'Updated balance: entitled={balance.entitled_days}, used={balance.used_days}, pending={balance.pending_days}')

        except LeaveBalance.DoesNotExist:
            logger.warning(f'No leave balance found for {getattr(leave_request.employee, "username", "?")} - {getattr(leave_request.leave_type, "name", "?")} - {getattr(leave_request.start_date, "year", "?")})')
            # If no balance exists, nothing to update
            pass
        except Exception as e:
            logger.error(f'Error updating leave balance: {str(e)}', exc_info=True)
            # Re-raise so calling views receive a 500 and log includes traceback
            raise
    
    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """Get leave requests pending approval for current user's role"""
        user = request.user
        user_role = getattr(user, 'role', None)
        
        # Filter requests based on user's role and approval stage
        if user_role == 'manager':
            # Managers see requests pending their approval
            pending_requests = self.get_queryset().filter(status='pending')
            # Exclude CEO-first affiliates (SDSL/SBL) and CEO self-requests from manager queue
            pending_requests = pending_requests.exclude(
                Q(employee__affiliate__name__in=['SDSL', 'SBL']) |
                Q(employee__department__affiliate__name__in=['SDSL', 'SBL']) |
                Q(employee__role='ceo')
            )
        elif user_role == 'hr':
            # HR sees items where HR is the required approver at the current status,
            # across affiliates and special cases (e.g., manager/HR self-requests).
            from .services import ApprovalWorkflowService
            candidates = self.get_queryset().filter(status__in=['pending', 'manager_approved', 'ceo_approved'])
            ids = []
            for req in candidates:
                if ApprovalWorkflowService.can_user_approve(req, user):
                    ids.append(req.id)
            pending_requests = self.get_queryset().filter(id__in=ids)
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
            # For admin, default to manager-stage queue to avoid mixing stages in Manager UI
            # Admins can still browse all requests via list endpoints
            pending_requests = self.get_queryset().filter(status='pending')
            pending_requests = pending_requests.exclude(
                Q(employee__department__affiliate__name__in=['SDSL', 'SBL']) |
                Q(employee__affiliate__name__in=['SDSL', 'SBL']) |
                Q(employee__role='ceo')
            )
            pending_requests = pending_requests.exclude(
                Q(employee__affiliate__name__in=['SDSL', 'SBL']) |
                Q(employee__department__affiliate__name__in=['SDSL', 'SBL']) |
                Q(employee__role='ceo')
            )
        else:
            pending_requests = self.get_queryset().none()
        
        serializer = self.get_serializer(pending_requests, many=True)
        # Include pending early-return interrupts for managers/HODs
        interrupt_payload = []
        if user_role in ['manager', 'admin']:
            try:
                manageable_request_ids = list(self.get_queryset().values_list('id', flat=True))
                interrupts_qs = LeaveInterruptRequest.objects.filter(
                    type='staff_return',
                    status='pending_manager',
                    leave_request_id__in=manageable_request_ids
                ).select_related('leave_request__employee', 'leave_request__leave_type')
                interrupt_payload = LeaveInterruptRequestSerializer(interrupts_qs, many=True).data
            except Exception:
                interrupt_payload = []

        # Add summary information
        response_data = {
            'requests': serializer.data,
            'interrupts': interrupt_payload,
            'count': len(serializer.data),
            'interrupt_count': len(interrupt_payload),
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
    def pending_interrupts(self, request):
        """List early-return interrupts awaiting manager decision."""
        user = request.user
        user_role = getattr(user, 'role', None)
        if user_role not in ['manager', 'admin']:
            return Response({'detail': 'Only managers/admins can view interrupts'}, status=status.HTTP_403_FORBIDDEN)

        manageable_request_ids = list(self.get_queryset().values_list('id', flat=True))
        qs = LeaveInterruptRequest.objects.filter(
            type='staff_return',
            status='pending_manager',
            leave_request_id__in=manageable_request_ids
        ).select_related('leave_request__employee', 'leave_request__leave_type')
        data = LeaveInterruptRequestSerializer(qs, many=True).data
        return Response({'results': data, 'count': len(data)})

    @action(detail=False, methods=['get'])
    def approval_counts(self, request):
        """Manager-specific counts proxy so frontend can call /leaves/manager/approval_counts/.

        This mirrors the logic in `LeaveRequestViewSet.approval_counts` but uses
        the Manager viewset's `get_queryset()` so counts reflect manager/HR/CEO visibility rules.
        """
        import logging
        logger = logging.getLogger('leaves')
        user = request.user
        user_role = getattr(user, 'role', None)
        try:
            logger.info(f"manager.approval_counts called by user={getattr(user, 'username', None)} role={user_role} path={request.path}")
        except Exception:
            logger.exception('Failed to log manager.approval_counts call')

        counts = {'manager_approvals': 0, 'hr_approvals': 0, 'ceo_approvals': 0, 'total': 0}
        try:
            if user_role == 'manager':
                counts['manager_approvals'] = self.get_queryset().filter(status='pending').exclude(
                    Q(employee__department__affiliate__name__in=['SDSL', 'SBL']) |
                    Q(employee__affiliate__name__in=['SDSL', 'SBL']) |
                    Q(employee__role='ceo')
                ).count()
                # include early return interrupts awaiting manager
                counts['manager_approvals'] += LeaveInterruptRequest.objects.filter(type='staff_return', status='pending_manager').count()
            elif user_role == 'hr':
                merban_count = self.get_queryset().filter(status='manager_approved').exclude(
                    Q(employee__department__affiliate__name__in=['SDSL', 'SBL']) |
                    Q(employee__affiliate__name__in=['SDSL', 'SBL'])
                ).count()
                ceo_approved_count = self.get_queryset().filter(status='ceo_approved').count()
                pending_ceo_self = self.get_queryset().filter(status='pending', employee__role='ceo').count()
                interrupts_hr = LeaveInterruptRequest.objects.filter(type='staff_return', status='pending_hr').count()
                counts['hr_approvals'] = merban_count + ceo_approved_count + pending_ceo_self + interrupts_hr
            elif user_role == 'ceo':
                from .services import ApprovalWorkflowService
                ceo_count = 0
                candidate_qs = self.get_queryset().filter(status__in=['pending', 'hr_approved'])
                for req in candidate_qs:
                    handler = ApprovalWorkflowService.get_handler(req)
                    if handler.can_approve(user, req.status):
                        ceo_count += 1
                counts['ceo_approvals'] = ceo_count
            elif user_role == 'admin':
                counts['manager_approvals'] = self.get_queryset().filter(status='pending').exclude(
                    Q(employee__department__affiliate__name__in=['SDSL', 'SBL']) |
                    Q(employee__affiliate__name__in=['SDSL', 'SBL']) |
                    Q(employee__role='ceo')
                ).count()
                merban_count = self.get_queryset().filter(status='manager_approved').exclude(
                    Q(employee__department__affiliate__name__in=['SDSL', 'SBL']) |
                    Q(employee__affiliate__name__in=['SDSL', 'SBL'])
                ).count()
                ceo_approved_count = self.get_queryset().filter(status='ceo_approved').count()
                pending_ceo_self = self.get_queryset().filter(status='pending', employee__role='ceo').count()
                interrupts_hr = LeaveInterruptRequest.objects.filter(type='staff_return', status='pending_hr').count()
                counts['hr_approvals'] = merban_count + ceo_approved_count + pending_ceo_self + interrupts_hr
                counts['ceo_approvals'] = self.get_queryset().filter(status='hr_approved').count()

            counts['total'] = counts['manager_approvals'] + counts['hr_approvals'] + counts['ceo_approvals']
        except Exception as e:
            logger.error(f'Error computing manager approval_counts for user={getattr(user, "username", None)}: {str(e)}', exc_info=True)
            return Response({**counts, 'error': 'unable to compute counts'})

        return Response(counts)

    @action(detail=False, methods=['get'])
    def pending_recall_count(self, request):
        """Count manager recall requests awaiting this user's acceptance."""
        user = request.user
        count = LeaveInterruptRequest.objects.filter(
            leave_request__employee=user,
            type='manager_recall',
            status='pending_staff'
        ).count()
        return Response({'recall_pending': count})

    @action(detail=False, methods=['get'])
    def hr_approvals_categorized(self, request):
        """Expose HR categorization via manager prefix so HR UI can call `/leaves/manager/hr_approvals_categorized/`."""
        # Reuse the logic from LeaveRequestViewSet but operate on this viewset's queryset
        import logging
        logger = logging.getLogger('leaves')
        user = request.user
        if getattr(user, 'role', None) != 'hr' and not getattr(user, 'is_superuser', False):
            return Response({'detail': 'Only HR can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)

        from .services import ApprovalWorkflowService, ApprovalRoutingService
        candidate_qs = self.get_queryset().filter(
            Q(status__in=['manager_approved', 'ceo_approved']) |
            Q(status='pending', employee__role='ceo')
        )
        logger.info(f"Manager HR categorization: Found {candidate_qs.count()} candidate requests")

        groups = {'Merban Capital': [], 'SDSL': [], 'SBL': []}

        for req in candidate_qs.select_related('employee__department__affiliate', 'employee__affiliate'):
            try:
                # HR must see ceo_approved (SDSL/SBL) even if can_user_approve is strict; allow override
                can_approve = ApprovalWorkflowService.can_user_approve(req, user)
                if req.status == 'ceo_approved' and getattr(user, 'role', None) == 'hr':
                    can_approve = True
                aff_name = ApprovalRoutingService.get_employee_affiliate_name(req.employee)
                if not can_approve:
                    continue
                if aff_name in ['MERBAN', 'MERBAN CAPITAL']:
                    key = 'Merban Capital'
                elif aff_name == 'SDSL':
                    key = 'SDSL'
                elif aff_name == 'SBL':
                    key = 'SBL'
                else:
                    continue
                groups[key].append(req)
            except Exception as e:
                logger.error(f"Manager HR categorization: Error processing LR#{getattr(req, 'id', 'unknown')}: {e}")
                continue

        # Include early-return interrupts awaiting HR
        interrupts_qs = LeaveInterruptRequest.objects.filter(type='staff_return', status='pending_hr').select_related('leave_request__employee', 'leave_request__employee__affiliate', 'leave_request__employee__department__affiliate', 'leave_request__leave_type')
        interrupts_data = LeaveInterruptRequestSerializer(interrupts_qs, many=True).data
        for interrupt, raw in zip(interrupts_qs, interrupts_data):
            try:
                aff_name = ApprovalRoutingService.get_employee_affiliate_name(interrupt.leave_request.employee)
                key = 'Merban Capital'
                if aff_name == 'SDSL':
                    key = 'SDSL'
                elif aff_name == 'SBL':
                    key = 'SBL'
                groups[key].append({**raw, '_is_interrupt': True})
            except Exception:
                continue

        serialized_groups = {k: self.get_serializer([req for req in v if not isinstance(req, dict)], many=True).data for k, v in groups.items()}
        # append interrupts already serialized
        for k in groups:
            for item in groups[k]:
                if isinstance(item, dict) and item.get('_is_interrupt'):
                    serialized_groups.setdefault(k, []).append(item)

        counts = {k: len(serialized_groups.get(k, [])) for k in groups.keys()}
        return Response({'groups': serialized_groups, 'counts': counts, 'total': sum(counts.values())})

    @action(detail=False, methods=['get'])
    def recent_activity(self, request):
        """Expose recent_activity via manager prefix so dashboard/CEO/HR calls succeed."""
        user = request.user
        role = getattr(user, 'role', None)
        try:
            limit = int(request.query_params.get('limit', 15))
        except Exception:
            limit = 15

        qs = LeaveRequest.objects.all()

        if getattr(user, 'is_superuser', False) or role == 'admin':
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
        data = LeaveRequestListSerializer(acted_qs, many=True).data
        return Response({'count': len(data), 'results': data})

    @action(detail=False, methods=['get'])
    def ceo_approvals_categorized(self, request):
        """CEO-specific endpoint exposed under manager prefix so frontend calls succeed.

        Mirrors the logic in `LeaveRequestViewSet.ceo_approvals_categorized` but uses
        this viewset's queryset to respect manager/HR/CEO visibility rules.
        """
        import logging
        logger = logging.getLogger('leaves')
        user = request.user
        user_role = getattr(user, 'role', None)
        if user_role != 'ceo' and not getattr(user, 'is_superuser', False):
            return Response({'detail': 'Only CEOs can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)

        from .services import ApprovalWorkflowService
        affiliate_filter = (request.query_params.get('affiliate') or '').strip().upper()
        # Default affiliate scope for superusers hitting the generic CEO page: Merban only
        if affiliate_filter == '' and getattr(user, 'is_superuser', False) and user_role != 'ceo':
            affiliate_filter = 'MERBAN CAPITAL'

        if getattr(user, 'is_superuser', False) and user_role != 'ceo':
            # Admin view should only show items actually at CEO stage per affiliate
            if affiliate_filter in ['', 'MERBAN CAPITAL', 'MERBAN']:
                candidate_qs = self.get_queryset().filter(status='hr_approved').exclude(employee__role='ceo')
                candidate_qs = candidate_qs.filter(
                    Q(employee__affiliate__name__iexact='MERBAN CAPITAL') |
                    Q(employee__department__affiliate__name__iexact='MERBAN CAPITAL') |
                    Q(employee__affiliate__name__iexact='MERBAN') |
                    Q(employee__department__affiliate__name__iexact='MERBAN')
                )
            else:
                candidate_qs = self.get_queryset().filter(status='pending').exclude(employee__role='ceo')
                candidate_qs = candidate_qs.filter(
                    Q(employee__affiliate__name__iexact=affiliate_filter) |
                    Q(employee__department__affiliate__name__iexact=affiliate_filter)
                )
        else:
            candidate_qs = self.get_queryset().filter(status__in=['pending', 'hr_approved']).exclude(employee__role='ceo')
            if affiliate_filter:
                candidate_qs = candidate_qs.filter(
                    Q(employee__affiliate__name__iexact=affiliate_filter) |
                    Q(employee__department__affiliate__name__iexact=affiliate_filter)
                )
        ids = []
        for req in candidate_qs:
            try:
                if ApprovalWorkflowService.can_user_approve(req, user):
                    ids.append(req.id)
            except Exception as e:
                logger.error(f'Error checking approval handler for LR#{getattr(req, "id", "unknown")}: {e}')
                continue

        pending_requests = self.get_queryset().filter(id__in=ids)
        serializer = self.get_serializer(pending_requests, many=True)

        categorized = {'hod_manager': [], 'hr': [], 'staff': []}
        for request_data in serializer.data:
            submitter_role = request_data.get('employee_role', 'staff')
            if submitter_role == 'ceo':
                continue
            if submitter_role in ['manager', 'hod']:
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

        # Also provide CEO affiliate hint used by frontend for tab selection
        try:
            ceo_aff = getattr(getattr(user, 'affiliate', None), 'name', '')
            response_data['ceo_affiliate'] = ceo_aff
        except Exception:
            response_data['ceo_affiliate'] = ''

        return Response(response_data)

    @action(detail=True, methods=['put'])
    def approve(self, request, pk=None):
        """Approve a request from the manager-facing endpoint.

        This mirrors the approval flow implemented in `LeaveRequestViewSet.approve` but
        runs in the ManagerLeaveViewSet context so URLs like `/leaves/manager/<id>/approve/`
        resolve correctly for the frontend.
        """
        import logging
        from notifications.services import LeaveNotificationService
        from .services import ApprovalWorkflowService
        logger = logging.getLogger('leaves')

        try:
            leave_request = self.get_object()
            user = request.user
            comments = request.data.get('approval_comments', '')

            logger.info(f'Attempting to approve leave request {pk} by user {user.username} (role: {getattr(user, "role", "unknown")})')

            # Authorization
            can_act = self._user_can_act_on(user, leave_request)
            if not can_act:
                logger.warning(f'User {getattr(user, "email", None)} denied action on LR#{pk}: _user_can_act_on returned False')
                return Response({'error': 'You are not allowed to act on this request'}, status=status.HTTP_403_FORBIDDEN)

            if leave_request.status == 'rejected':
                return Response({'error': 'Cannot approve a rejected request'}, status=status.HTTP_400_BAD_REQUEST)
            elif leave_request.status == 'approved':
                return Response({'error': 'Request is already fully approved'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                ApprovalWorkflowService.approve_request(leave_request, user, comments)

                # Send notifications and update balance on final approval
                if leave_request.status == 'manager_approved':
                    LeaveNotificationService.notify_manager_approval(leave_request, user)
                    message = 'Leave request approved by manager'
                elif leave_request.status == 'hr_approved':
                    LeaveNotificationService.notify_hr_approval(leave_request, user)
                    message = 'Leave request approved by HR'
                elif leave_request.status == 'approved':
                    LeaveNotificationService.notify_ceo_approval(leave_request, user)
                    self._update_leave_balance(leave_request, 'approve')
                    message = 'Leave request given final approval'
                else:
                    message = 'Leave request approved'

            except PermissionDenied as pd:
                error_msg = str(pd) if str(pd) else 'You do not have permission to approve this request at this stage'
                logger.warning(f'Permission denied for request {pk} approval by {getattr(user, "username", None)}: {error_msg}')
                return Response({'error': error_msg}, status=status.HTTP_403_FORBIDDEN)
            except ValueError as ve:
                logger.warning(f'Approval validation failed for request {pk}: {str(ve)}')
                return Response({'error': str(ve)}, status=status.HTTP_403_FORBIDDEN)

            return Response({'message': message, 'current_status': leave_request.status})

        except Exception as e:
            logger.error(f'Error approving leave request {pk}: {str(e)}', exc_info=True)
            return Response({'error': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['put'])
    def reject(self, request, pk=None):
        """Reject a request from the manager-facing endpoint."""
        import logging
        from notifications.services import LeaveNotificationService
        logger = logging.getLogger('leaves')

        try:
            leave_request = self.get_object()
            user = request.user
            comments = request.data.get('approval_comments', '')

            logger.info(f'Attempting to reject leave request {pk} by user {getattr(user, "username", None)}')

            if not self._user_can_act_on(user, leave_request):
                return Response({'error': 'You are not allowed to act on this request'}, status=status.HTTP_403_FORBIDDEN)

            if leave_request.status in ['rejected', 'cancelled']:
                return Response({'error': 'Request is already rejected or cancelled'}, status=status.HTTP_400_BAD_REQUEST)

            user_role = getattr(user, 'role', None)
            rejection_stage = None
            if user_role == 'manager' and leave_request.status == 'pending':
                rejection_stage = 'manager'
            elif user_role == 'hr' and leave_request.status in ['pending', 'manager_approved', 'ceo_approved']:
                rejection_stage = 'hr'
            elif user_role in ['ceo', 'admin'] and leave_request.status in ['pending', 'manager_approved', 'hr_approved']:
                rejection_stage = user_role.replace('admin', 'ceo')
            elif user_role == 'admin':
                rejection_stage = 'admin'
            else:
                return Response({'error': f'Cannot reject this request. Current stage: {leave_request.current_approval_stage}, your role: {user_role}'}, status=status.HTTP_403_FORBIDDEN)

            leave_request.reject(user, comments, rejection_stage)
            LeaveNotificationService.notify_rejection(leave_request, user, rejection_stage)
            self._update_leave_balance(leave_request, 'reject')

            logger.info(f'Successfully rejected leave request {pk} at {rejection_stage} level')
            return Response({'message': f'Leave request rejected by {rejection_stage}', 'current_status': leave_request.status})

        except Exception as e:
            logger.error(f'Error rejecting leave request {pk}: {str(e)}', exc_info=True)
            return Response({'error': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='recall')
    def recall_staff(self, request, pk=None):
        """Manager/HOD initiates a recall on an approved leave (staff must accept)."""
        leave = self.get_object()
        user = request.user
        if not self._can_initiate_recall(user, leave):
            return Response({'detail': 'Not allowed to recall this leave.'}, status=status.HTTP_403_FORBIDDEN)
        if leave.status != 'approved':
            return Response({'detail': 'Recall only applies to approved requests.'}, status=status.HTTP_400_BAD_REQUEST)

        resume_date_raw = request.data.get('resume_date')
        reason = request.data.get('reason', '')
        if not resume_date_raw:
            return Response({'detail': 'resume_date is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from datetime import date
            resume_date = date.fromisoformat(resume_date_raw)
        except Exception:
            return Response({'detail': 'Invalid resume_date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        if resume_date < leave.start_date or resume_date > leave.end_date:
            return Response({'detail': 'Resume date must be between start_date and end_date.'}, status=status.HTTP_400_BAD_REQUEST)

        credited = self._calculate_credited_working_days(resume_date, leave.end_date)
        if credited <= 0:
            return Response({'detail': 'No working days remain to credit.'}, status=status.HTTP_400_BAD_REQUEST)

        interrupt = LeaveInterruptRequest.objects.create(
            leave_request=leave,
            type='manager_recall',
            status='pending_staff',
            requested_resume_date=resume_date,
            reason=reason,
            initiated_by=user,
            initiated_role=getattr(user, 'role', '')
        )
        LeaveInterruptLog.objects.create(leave_request=leave, interrupt_request=interrupt, actor=user, event='requested', comment=reason, credited_days=credited)
        return Response({'detail': 'Recall sent to staff for confirmation.', 'interrupt_id': interrupt.id}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='interrupts/(?P<interrupt_id>[^/.]+)/manager-approve')
    def approve_return(self, request, interrupt_id=None):
        """Manager approves staff-initiated early return (moves to HR)."""
        try:
            interrupt = LeaveInterruptRequest.objects.get(id=interrupt_id, type='staff_return')
        except LeaveInterruptRequest.DoesNotExist:
            return Response({'detail': 'Interrupt not found.'}, status=status.HTTP_404_NOT_FOUND)
        leave = interrupt.leave_request
        if not self._user_can_act_on(request.user, leave):
            return Response({'detail': 'Not allowed.'}, status=status.HTTP_403_FORBIDDEN)
        if interrupt.status != 'pending_manager':
            return Response({'detail': 'Interrupt is not awaiting manager approval.'}, status=status.HTTP_400_BAD_REQUEST)
        interrupt.status = 'pending_hr'
        interrupt.manager_decision_by = request.user
        interrupt.manager_decision_at = timezone.now()
        interrupt.manager_decision_comment = request.data.get('reason', '')
        interrupt.save(update_fields=['status', 'manager_decision_by', 'manager_decision_at', 'manager_decision_comment', 'updated_at'])
        LeaveInterruptLog.objects.create(leave_request=leave, interrupt_request=interrupt, actor=request.user, event='manager_approved', comment=interrupt.manager_decision_comment)
        return Response({'detail': 'Early return approved by manager; pending HR.'})

    @action(detail=False, methods=['post'], url_path='interrupts/(?P<interrupt_id>[^/.]+)/manager-reject')
    def reject_return(self, request, interrupt_id=None):
        """Manager rejects staff-initiated early return."""
        try:
            interrupt = LeaveInterruptRequest.objects.get(id=interrupt_id, type='staff_return')
        except LeaveInterruptRequest.DoesNotExist:
            return Response({'detail': 'Interrupt not found.'}, status=status.HTTP_404_NOT_FOUND)
        leave = interrupt.leave_request
        if not self._user_can_act_on(request.user, leave):
            return Response({'detail': 'Not allowed.'}, status=status.HTTP_403_FORBIDDEN)
        if interrupt.status != 'pending_manager':
            return Response({'detail': 'Interrupt is not awaiting manager approval.'}, status=status.HTTP_400_BAD_REQUEST)
        interrupt.status = 'rejected'
        interrupt.manager_decision_by = request.user
        interrupt.manager_decision_at = timezone.now()
        interrupt.manager_decision_comment = request.data.get('reason', '')
        interrupt.save(update_fields=['status', 'manager_decision_by', 'manager_decision_at', 'manager_decision_comment', 'updated_at'])
        LeaveInterruptLog.objects.create(leave_request=leave, interrupt_request=interrupt, actor=request.user, event='manager_rejected', comment=interrupt.manager_decision_comment)
        try:
            leave.interruption_note = f"Early return rejected by manager on {interrupt.manager_decision_at.date()} — {interrupt.manager_decision_comment}".strip()
            leave.interrupted_at = interrupt.manager_decision_at
            leave.interrupted_by = request.user
            leave.save(update_fields=['interruption_note', 'interrupted_at', 'interrupted_by', 'updated_at'])
        except Exception:
            pass
        return Response({'detail': 'Early return rejected.'})

    @action(detail=False, methods=['post'], url_path='interrupts/(?P<interrupt_id>[^/.]+)/ceo-approve')
    def ceo_approve_return(self, request, interrupt_id=None):
        """CEO approves early return. For SDSL/SBL, moves to HR; for HR-initiated Merban, applies directly."""
        try:
            interrupt = LeaveInterruptRequest.objects.get(id=interrupt_id, type='staff_return')
        except LeaveInterruptRequest.DoesNotExist:
            return Response({'detail': 'Interrupt not found.'}, status=status.HTTP_404_NOT_FOUND)

        leave = interrupt.leave_request
        role = getattr(request.user, 'role', None)
        if role not in ['ceo'] and not getattr(request.user, 'is_superuser', False) and getattr(request.user, 'role', None) != 'admin':
            return Response({'detail': 'Only CEO/Admin can approve at this stage.'}, status=status.HTTP_403_FORBIDDEN)
        if interrupt.status != 'pending_ceo':
            return Response({'detail': 'Interrupt is not awaiting CEO approval.'}, status=status.HTTP_400_BAD_REQUEST)

        aff = ApprovalRoutingService.get_employee_affiliate_name(getattr(leave, 'employee', None))
        initiator_role = self._normalize_role(interrupt.initiated_role or getattr(getattr(leave, 'employee', None), 'role', ''))
        comment = request.data.get('reason', '')

        # Log CEO approval
        LeaveInterruptLog.objects.create(leave_request=leave, interrupt_request=interrupt, actor=request.user, event='ceo_approved', comment=comment)

        # SDSL/SBL staff flow: CEO first, then HR final approval
        if aff in ['SDSL', 'SBL'] and initiator_role != 'ceo':
            interrupt.status = 'pending_hr'
            interrupt.save(update_fields=['status', 'updated_at'])
            return Response({'detail': 'Early return approved by CEO; pending HR.'})

        # CEO is final approver (e.g., Merban HR-initiated)
        credited = self._calculate_credited_working_days(interrupt.requested_resume_date, leave.end_date)
        interrupt.reason = interrupt.reason or comment
        interrupt.save(update_fields=['reason', 'updated_at'])
        self._apply_interrupt(leave, interrupt, request.user)
        return Response({'detail': 'Early return approved and applied.', 'credited_days': credited})

    @action(detail=False, methods=['post'], url_path='interrupts/(?P<interrupt_id>[^/.]+)/ceo-reject')
    def ceo_reject_return(self, request, interrupt_id=None):
        """CEO rejects an early return awaiting CEO approval."""
        try:
            interrupt = LeaveInterruptRequest.objects.get(id=interrupt_id, type='staff_return')
        except LeaveInterruptRequest.DoesNotExist:
            return Response({'detail': 'Interrupt not found.'}, status=status.HTTP_404_NOT_FOUND)

        role = getattr(request.user, 'role', None)
        if role not in ['ceo'] and not getattr(request.user, 'is_superuser', False) and getattr(request.user, 'role', None) != 'admin':
            return Response({'detail': 'Only CEO/Admin can reject at this stage.'}, status=status.HTTP_403_FORBIDDEN)
        if interrupt.status != 'pending_ceo':
            return Response({'detail': 'Interrupt is not awaiting CEO approval.'}, status=status.HTTP_400_BAD_REQUEST)

        interrupt.status = 'rejected'
        interrupt.save(update_fields=['status', 'updated_at'])
        comment = request.data.get('reason', '')
        LeaveInterruptLog.objects.create(leave_request=interrupt.leave_request, interrupt_request=interrupt, actor=request.user, event='ceo_rejected', comment=comment)
        try:
            leave = interrupt.leave_request
            leave.interruption_note = f"Early return rejected by CEO on {timezone.now().date()} — {comment}".strip()
            leave.interrupted_at = timezone.now()
            leave.interrupted_by = request.user
            leave.save(update_fields=['interruption_note', 'interrupted_at', 'interrupted_by', 'updated_at'])
        except Exception:
            pass
        return Response({'detail': 'Early return rejected.'})

    @action(detail=False, methods=['post'], url_path='interrupts/(?P<interrupt_id>[^/.]+)/hr-approve')
    def hr_approve_return(self, request, interrupt_id=None):
        """HR approves staff early return and applies credit."""
        try:
            interrupt = LeaveInterruptRequest.objects.get(id=interrupt_id, type='staff_return')
        except LeaveInterruptRequest.DoesNotExist:
            return Response({'detail': 'Interrupt not found.'}, status=status.HTTP_404_NOT_FOUND)
        leave = interrupt.leave_request
        if getattr(request.user, 'role', None) not in ['hr', 'admin'] and not getattr(request.user, 'is_superuser', False):
            return Response({'detail': 'Only HR/Admin can approve at this stage.'}, status=status.HTTP_403_FORBIDDEN)
        if interrupt.status != 'pending_hr':
            return Response({'detail': 'Interrupt is not awaiting HR approval.'}, status=status.HTTP_400_BAD_REQUEST)
        interrupt.status = 'approved'
        interrupt.hr_decision_by = request.user
        interrupt.hr_decision_at = timezone.now()
        interrupt.hr_decision_comment = request.data.get('reason', '')
        interrupt.save(update_fields=['status', 'hr_decision_by', 'hr_decision_at', 'hr_decision_comment', 'updated_at'])
        # Apply credit inclusively
        credited = self._calculate_credited_working_days(interrupt.requested_resume_date, leave.end_date)
        interrupt.credited_working_days = credited
        interrupt.applied_at = timezone.now()
        interrupt.save(update_fields=['credited_working_days', 'applied_at'])

        # Apply to leave and balance
        leave.interruption_credited_days = credited
        leave.interruption_note = f"Early return on {interrupt.requested_resume_date} — {credited} days credited. Reason: {interrupt.reason}"
        leave.interrupted_at = interrupt.applied_at
        leave.interrupted_by = request.user
        leave.save(update_fields=['interruption_credited_days', 'interruption_note', 'interrupted_at', 'interrupted_by', 'updated_at'])
        try:
            balance = LeaveBalance.objects.filter(employee=leave.employee, leave_type=leave.leave_type, year=leave.start_date.year).first()
            if balance:
                balance.update_balance()
        except Exception:
            pass
        LeaveInterruptLog.objects.create(leave_request=leave, interrupt_request=interrupt, actor=request.user, event='applied', credited_days=credited, comment=interrupt.hr_decision_comment)
        return Response({'detail': 'Early return approved and applied.', 'credited_days': credited})

    @action(detail=False, methods=['post'], url_path='interrupts/(?P<interrupt_id>[^/.]+)/hr-reject')
    def hr_reject_return(self, request, interrupt_id=None):
        """HR rejects staff early return when pending HR."""
        try:
            interrupt = LeaveInterruptRequest.objects.get(id=interrupt_id, type='staff_return')
        except LeaveInterruptRequest.DoesNotExist:
            return Response({'detail': 'Interrupt not found.'}, status=status.HTTP_404_NOT_FOUND)
        leave = interrupt.leave_request
        if getattr(request.user, 'role', None) not in ['hr', 'admin'] and not getattr(request.user, 'is_superuser', False):
            return Response({'detail': 'Only HR/Admin can reject at this stage.'}, status=status.HTTP_403_FORBIDDEN)
        if interrupt.status != 'pending_hr':
            return Response({'detail': 'Interrupt is not awaiting HR approval.'}, status=status.HTTP_400_BAD_REQUEST)
        interrupt.status = 'rejected'
        interrupt.hr_decision_by = request.user
        interrupt.hr_decision_at = timezone.now()
        interrupt.hr_decision_comment = request.data.get('reason', '')
        interrupt.save(update_fields=['status', 'hr_decision_by', 'hr_decision_at', 'hr_decision_comment', 'updated_at'])
        LeaveInterruptLog.objects.create(leave_request=leave, interrupt_request=interrupt, actor=request.user, event='hr_rejected', comment=interrupt.hr_decision_comment)
        try:
            leave.interruption_note = f"Early return rejected by HR on {interrupt.hr_decision_at.date()} — {interrupt.hr_decision_comment}".strip()
            leave.interrupted_at = interrupt.hr_decision_at
            leave.interrupted_by = request.user
            leave.save(update_fields=['interruption_note', 'interrupted_at', 'interrupted_by', 'updated_at'])
        except Exception:
            pass
        return Response({'detail': 'Early return rejected.'})

    @action(detail=False, methods=['get'], url_path='export_all/all')
    def export_all(self, request):
        """Export leave requests as CSV for audit.

        - HR and Admin can export all requests across affiliates.
        - CEO and superusers may also export all requests.
        - Other users are forbidden from exporting all requests.
        The CSV includes employee, email, affiliate, department, leave type, dates,
        total days, status, reason, approval comments, created_at, manager/hr/ceo approval dates,
        and a final approval/rejection date chosen per affiliate rules.
        """
        return export_all_handler(request)

    

    @action(detail=False, methods=['get'], url_path='export-all/all')
    def export_all_hyphen(self, request):
        """Alias endpoint for export_all to support hyphen URL used by some clients."""
        return self.export_all(request)

    @action(detail=False, methods=['get'], url_path='export_all_list')
    def export_all_list(self, request):
        """Safe alias endpoint that avoids DRF router pk collisions.

        Some routers will interpret an action path segment that looks like a
        primary-key as a detail route (causing 404s). This alias uses a
        non-ambiguous name that will always be registered as a list-action.
        """
        return self.export_all(request)

    @action(detail=True, methods=['put', 'post'])
    def cancel(self, request, pk=None):
        """Requester-only cancel under manager prefix to match frontend route.

        Rules:
        - Only the original requester can cancel their own request
        - Only while status is 'pending' (before any approval/rejection)
        - Works regardless of requester role (staff/manager/hr), the path uses
          the manager prefix for frontend consistency.
        """
        logger = logging.getLogger('leaves')

        # Unrestricted lookup; permission is enforced by model's can_be_cancelled
        try:
            leave_request = LeaveRequest.objects.select_related('employee', 'leave_type').get(pk=pk)
        except LeaveRequest.DoesNotExist:
            return Response({'error': 'Leave request not found'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        comments = request.data.get('comments', '')
        logger.info(f'[Manager prefix] Attempting to cancel LR#{pk} by user {getattr(user, "username", None)}')

        success, status_code, message = _perform_cancel_action(leave_request, user, comments, self._update_leave_balance)
        if not success:
            return Response({'error': message}, status=status_code)

        logger.info(f'Leave request {pk} cancelled by {getattr(user, "username", None)}')
        return Response({
            'message': 'Leave request cancelled successfully',
            'status': getattr(leave_request, 'status', 'cancelled')
        }, status=status_code)


# Module-level proxy view to expose the exporter via a stable URL.
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_all_proxy(request):
    """Proxy endpoint that delegates to LeaveRequestViewSet.export_all.

    Using a function-based DRF view avoids issues where the ViewSet's
    bound method cannot be located by the as_view mapping in some reload
    scenarios. This simply constructs a viewset and calls the existing
    exporter method so all logic and permission checks remain in one place.
    """
    return export_all_handler(request)


def export_all_handler(request):
    """Shared handler implementing the CSV export logic.

    Kept at module level so it can be called from class methods, proxies,
    and tests without depending on ViewSet binding semantics.

    Includes comprehensive audit fields: original request data, approval dates,
    interrupt/recall/early-return details, resume events, and credited days.
    """
    import csv
    import io

    user = request.user
    role = getattr(user, 'role', None)
    if not (getattr(user, 'is_superuser', False) or role in ['hr', 'admin', 'ceo']):
        return Response({'detail': 'Only HR, Admin or CEO can export all leave requests'}, status=status.HTTP_403_FORBIDDEN)

    qs = LeaveRequest.objects.select_related(
        'employee', 'employee__affiliate', 'employee__department', 'leave_type', 'approved_by'
    ).prefetch_related('interrupt_requests', 'resume_events')

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    # Enhanced headers with interrupt/recall/resume audit fields
    writer.writerow([
        'Employee', 'Employee Email', 'Affiliate', 'Department', 'Leave Type',
        'Start Date', 'End Date', 'Total Days', 'Status', 'Reason', 'Approval Comments', 'Created At',
        'Manager Approval Date', 'HR Approval Date', 'CEO Approval Date', 'Final Approval/Rejection Date',
        # Interrupt/Recall/Early Return fields
        'Has Recall', 'Recall Type', 'Recall Status', 'Recall Requested Date', 'Recall Reason',
        'Recall Initiated By', 'Recall Manager Decision Date', 'Recall HR Decision Date',
        'Recall Credited Days', 'Recall Applied Date',
        # Resume fields
        'Has Resume Record', 'Actual Resume Date', 'Resume Recorded By', 'Resume Recorded At',
        # Summary fields
        'Interruption Note', 'Days Credited Back'
    ])

    for req in qs.order_by('-created_at'):
        emp = getattr(req, 'employee', None)
        affiliate = None
        try:
            affiliate = getattr(emp, 'affiliate', None) or getattr(getattr(emp, 'department', None), 'affiliate', None)
            aff_name = affiliate.name if affiliate else ''
        except Exception:
            aff_name = ''

        dept = getattr(getattr(emp, 'department', None), 'name', '') if emp else ''
        emp_name = getattr(emp, 'get_full_name', lambda: getattr(emp, 'username', ''))() if emp else ''
        emp_email = getattr(emp, 'email', '') if emp else ''

        mgr_date = getattr(req, 'manager_approval_date', '')
        hr_date = getattr(req, 'hr_approval_date', '')
        ceo_date = getattr(req, 'ceo_approval_date', '')

        final_date = ''
        try:
            aff_key = (aff_name or '').strip().upper()
            if aff_key == 'MERBAN CAPITAL':
                final_date = ceo_date or ''
            else:
                final_date = hr_date or ceo_date or ''
        except Exception:
            final_date = hr_date or ceo_date or ''

        # Get interrupt/recall data (most recent approved or any pending)
        interrupt = req.interrupt_requests.order_by('-created_at').first()
        has_recall = 'Yes' if interrupt else 'No'
        recall_type = ''
        recall_status = ''
        recall_requested_date = ''
        recall_reason = ''
        recall_initiated_by = ''
        recall_mgr_decision = ''
        recall_hr_decision = ''
        recall_credited = ''
        recall_applied = ''

        if interrupt:
            recall_type = 'Manager Recall' if interrupt.type == 'manager_recall' else 'Early Return'
            recall_status = interrupt.get_status_display() if hasattr(interrupt, 'get_status_display') else interrupt.status
            recall_requested_date = interrupt.requested_resume_date or ''
            recall_reason = interrupt.reason or ''
            if interrupt.initiated_by:
                recall_initiated_by = interrupt.initiated_by.get_full_name() if hasattr(interrupt.initiated_by, 'get_full_name') else str(interrupt.initiated_by)
            recall_mgr_decision = interrupt.manager_decision_at.date() if interrupt.manager_decision_at else ''
            recall_hr_decision = interrupt.hr_decision_at.date() if interrupt.hr_decision_at else ''
            recall_credited = interrupt.credited_working_days or ''
            recall_applied = interrupt.applied_at.date() if interrupt.applied_at else ''

        # Get resume event data
        resume_event = req.resume_events.order_by('-created_at').first()
        has_resume = 'Yes' if resume_event else 'No'
        resume_date = ''
        resume_recorded_by = ''
        resume_recorded_at = ''

        if resume_event:
            resume_date = resume_event.resume_date or ''
            if resume_event.recorded_by:
                resume_recorded_by = resume_event.recorded_by.get_full_name() if hasattr(resume_event.recorded_by, 'get_full_name') else str(resume_event.recorded_by)
            resume_recorded_at = resume_event.created_at.date() if resume_event.created_at else ''

        # Get summary fields from leave request
        interruption_note = getattr(req, 'interruption_note', '') or ''
        days_credited = getattr(req, 'interruption_credited_days', '') or ''

        writer.writerow([
            emp_name,
            emp_email,
            aff_name,
            dept,
            getattr(getattr(req, 'leave_type', None), 'name', ''),
            getattr(req, 'start_date', ''),
            getattr(req, 'end_date', ''),
            getattr(req, 'total_days', ''),
            getattr(req, 'status', ''),
            getattr(req, 'reason', ''),
            getattr(req, 'approval_comments', ''),
            getattr(req, 'created_at', ''),
            mgr_date,
            hr_date,
            ceo_date,
            final_date,
            # Interrupt/Recall fields
            has_recall,
            recall_type,
            recall_status,
            recall_requested_date,
            recall_reason,
            recall_initiated_by,
            recall_mgr_decision,
            recall_hr_decision,
            recall_credited,
            recall_applied,
            # Resume fields
            has_resume,
            resume_date,
            resume_recorded_by,
            resume_recorded_at,
            # Summary fields
            interruption_note,
            days_credited,
        ])

    resp = io.BytesIO()
    resp.write(buffer.getvalue().encode('utf-8'))
    resp.seek(0)

    from django.http import HttpResponse
    response = HttpResponse(resp.read(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="all_leave_requests.csv"'
    return response

    @action(detail=False, methods=['get'])
    def ceo_approvals_categorized(self, request):
        """CEO-specific endpoint that categorizes pending requests by submitter role"""
        import logging
        logger = logging.getLogger('leaves')
        user = request.user
        user_role = getattr(user, 'role', None)
        
        if user_role != 'ceo' and not getattr(user, 'is_superuser', False):
            return Response({'detail': 'Only CEOs can access this endpoint'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Get all requests pending CEO approval (Merban: hr_approved; SDSL/SBL: pending)
        from .services import ApprovalWorkflowService
        affiliate_filter = (request.query_params.get('affiliate') or '').strip().upper()
        if affiliate_filter == '' and getattr(user, 'is_superuser', False) and user_role != 'ceo':
            affiliate_filter = 'MERBAN CAPITAL'

        # For superusers/admins, enforce stage-specific filtering per affiliate to avoid pre-stage leakage
        if getattr(user, 'is_superuser', False) and user_role != 'ceo':
            # Default Merban view: CEO acts after HR, so only hr_approved items should appear
            if affiliate_filter in ['', 'MERBAN CAPITAL', 'MERBAN']:
                candidate_qs = self.get_queryset().filter(status='hr_approved').exclude(employee__role='ceo')
                candidate_qs = candidate_qs.filter(
                    Q(employee__affiliate__name__iexact='MERBAN CAPITAL') |
                    Q(employee__department__affiliate__name__iexact='MERBAN CAPITAL') |
                    Q(employee__affiliate__name__iexact='MERBAN') |
                    Q(employee__department__affiliate__name__iexact='MERBAN')
                )
            else:
                # SDSL/SBL CEO-first flow: CEO approves at pending stage
                candidate_qs = self.get_queryset().filter(status='pending').exclude(employee__role='ceo')
                candidate_qs = candidate_qs.filter(
                    Q(employee__affiliate__name__iexact=affiliate_filter) |
                    Q(employee__department__affiliate__name__iexact=affiliate_filter)
                )
        else:
            candidate_qs = self.get_queryset().filter(status__in=['pending', 'hr_approved']).exclude(employee__role='ceo')
            if affiliate_filter:
                candidate_qs = candidate_qs.filter(
                    Q(employee__affiliate__name__iexact=affiliate_filter) |
                    Q(employee__department__affiliate__name__iexact=affiliate_filter)
                )
        ids = []
        for req in candidate_qs:
            if ApprovalWorkflowService.can_user_approve(req, user):
                ids.append(req.id)
        pending_requests = self.get_queryset().filter(id__in=ids)
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
            if submitter_role == 'ceo':
                continue
            logger.debug(f"CEO approvals categorizing: LR#{request_data.get('id')} employee={request_data.get('employee_name')} role={submitter_role}")
            
            if submitter_role in ['manager', 'hod']:
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
    def hr_approvals_categorized(self, request):
        """HR-specific endpoint: categorize approvable pending requests by affiliate.

        Groups: Merban Capital, SDSL, SBL. Only includes requests where HR can approve now.
        """
        import logging
        logger = logging.getLogger('leaves')
        user = request.user
        if getattr(user, 'role', None) != 'hr' and not getattr(user, 'is_superuser', False):
            return Response({'detail': 'Only HR can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)

        from .services import ApprovalWorkflowService, ApprovalRoutingService
        # HR should only see items that are actually awaiting HR action:
        # - manager_approved (standard/Merban or manager/HOD skip)
        # - ceo_approved (CEO-first SDSL/SBL flow or HR self-request in those affiliates)
        candidate_qs = self.get_queryset().filter(status__in=['manager_approved', 'ceo_approved'])
        logger.info(f"HR categorization: Found {candidate_qs.count()} candidate requests with status manager_approved or ceo_approved")
        
        groups = {'Merban Capital': [], 'SDSL': [], 'SBL': []}

        for req in candidate_qs.select_related('employee__department__affiliate', 'employee__affiliate'):
            try:
                can_approve = ApprovalWorkflowService.can_user_approve(req, user)
                aff_name = ApprovalRoutingService.get_employee_affiliate_name(req.employee)
                logger.info(f"HR categorization: LR#{req.id} status={req.status} affiliate={aff_name} can_approve={can_approve}")
                
                if not can_approve:
                    continue
                    
                # Normalize common variants
                if aff_name in ['MERBAN', 'MERBAN CAPITAL']:
                    key = 'Merban Capital'
                elif aff_name == 'SDSL':
                    key = 'SDSL'
                elif aff_name == 'SBL':
                    key = 'SBL'
                else:
                    # Skip other affiliates for HR segmentation (still accessible via generic list)
                    logger.info(f"HR categorization: LR#{req.id} skipped - affiliate '{aff_name}' not in known groups")
                    continue
                groups[key].append(req)
                logger.info(f"HR categorization: LR#{req.id} added to {key} group")
            except Exception as e:
                logger.error(f"HR categorization: Error processing LR#{req.id}: {e}")
                continue

        # Serialize per group
        serialized_groups = {k: self.get_serializer(v, many=True).data for k, v in groups.items()}
        counts = {k: len(v) for k, v in groups.items()}
        return Response({'groups': serialized_groups, 'counts': counts, 'total': sum(counts.values())})

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
    
    @action(detail=True, methods=['put', 'post'])
    def cancel(self, request, pk=None):
        """Cancel a leave request (only allowed by the requester while status is pending)."""
        logger = logging.getLogger('leaves')

        # Use unrestricted lookup so requester can always find their record
        try:
            leave_request = LeaveRequest.objects.select_related('employee', 'leave_type').get(pk=pk)
        except LeaveRequest.DoesNotExist:
            return Response({'error': 'Leave request not found'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        comments = request.data.get('comments', '')
        logger.info(f'Attempting to cancel leave request {pk} by user {getattr(user, "username", None)}')

        success, status_code, message = _perform_cancel_action(leave_request, user, comments, self._update_leave_balance)
        if not success:
            return Response({'error': message}, status=status_code)

        logger.info(f'Leave request {pk} cancelled by {getattr(user, "username", None)}')
        return Response({
            'message': 'Leave request cancelled successfully',
            'status': getattr(leave_request, 'status', 'cancelled')
        }, status=status_code)

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
            
            logger.info(f'Attempting to approve leave request {pk} by user {user.username} (role: {getattr(user, "role", "unknown")}, affiliate: {getattr(getattr(user, "affiliate", None), "name", "None")})')
            
            # Authorization: ensure user can act on this request
            can_act = self._user_can_act_on(user, leave_request)
            logger.info(f'User can act on request: {can_act}')
            
            if not can_act:
                logger.warning(f'User {user.email} denied action on LR#{pk}: _user_can_act_on returned False')
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
                
            except PermissionDenied as pd:
                error_msg = str(pd) if str(pd) else 'You do not have permission to approve this request at this stage'
                logger.warning(f'Permission denied for request {pk} approval by {user.username}: {error_msg}')
                return Response({'error': error_msg}, status=status.HTTP_403_FORBIDDEN)
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
                counts['manager_approvals'] = self.get_queryset().filter(status='pending').exclude(
                    Q(employee__department__affiliate__name__in=['SDSL', 'SBL']) |
                    Q(employee__affiliate__name__in=['SDSL', 'SBL']) |
                    Q(employee__role='ceo')
                ).count()
            elif user_role == 'hr':
                # HR: Merban manager_approved + SDSL/SBL ceo_approved
                merban_count = self.get_queryset().filter(status='manager_approved').exclude(
                    Q(employee__department__affiliate__name__in=['SDSL', 'SBL']) |
                    Q(employee__affiliate__name__in=['SDSL', 'SBL'])
                ).count()
                ceo_approved_count = self.get_queryset().filter(status='ceo_approved').count()
                pending_ceo_self = self.get_queryset().filter(status='pending', employee__role='ceo').count()
                counts['hr_approvals'] = merban_count + ceo_approved_count + pending_ceo_self
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
                counts['manager_approvals'] = self.get_queryset().filter(status='pending').exclude(
                    Q(employee__department__affiliate__name__in=['SDSL', 'SBL']) |
                    Q(employee__affiliate__name__in=['SDSL', 'SBL']) |
                    Q(employee__role='ceo')
                ).count()
                merban_count = self.get_queryset().filter(status='manager_approved').exclude(
                    Q(employee__department__affiliate__name__in=['SDSL', 'SBL']) |
                    Q(employee__affiliate__name__in=['SDSL', 'SBL'])
                ).count()
                ceo_approved_count = self.get_queryset().filter(status='ceo_approved').count()
                pending_ceo_self = self.get_queryset().filter(status='pending', employee__role='ceo').count()
                counts['hr_approvals'] = merban_count + ceo_approved_count + pending_ceo_self
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
    Custom permission to only allow managers, HR, CEOs, and admins to approve/reject leaves
    """
    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        user = request.user
        try:
            from users.models import CustomUser
            if isinstance(user, CustomUser):
                return user.is_superuser or user.role in ['manager', 'hr', 'ceo', 'admin']
        except Exception:
            pass
        return getattr(user, 'is_superuser', False) or (
            hasattr(user, 'role') and getattr(user, 'role') in ['manager', 'hr', 'ceo', 'admin']
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
