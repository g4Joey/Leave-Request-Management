from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import LeaveRequest
from .serializers import LeaveRequestListSerializer
from .services import ApprovalWorkflowService

class IsCEOPermission(permissions.BasePermission):
    """Allow only CEO or superuser."""
    def has_permission(self, request, view):
        user = request.user
        return bool(getattr(user, 'is_superuser', False) or getattr(user, 'role', None) == 'ceo')

class CEOLeaveViewSet(viewsets.ReadOnlyModelViewSet):
    """Standalone CEO viewset with isolated filtering and approval actions."""
    serializer_class = LeaveRequestListSerializer
    permission_classes = [permissions.IsAuthenticated, IsCEOPermission]
    filter_backends = []  # Keep simple; explicit filtering logic below

    def get_queryset(self):
        user = self.request.user
        if not (getattr(user, 'is_superuser', False) or getattr(user, 'role', None) == 'ceo'):
            return LeaveRequest.objects.none()
        affiliate = getattr(getattr(user, 'affiliate', None), 'name', None)
        if not affiliate:
            return LeaveRequest.objects.none()
        qs = LeaveRequest.objects.select_related('employee__department__affiliate', 'employee__affiliate')
        aff_ilike = affiliate.lower()
        if aff_ilike == 'merban capital':
            # Merban CEO: sees hr_approved staff/manager requests, pending HR own requests, plus history
            base = qs.filter(
                Q(employee__affiliate__name__iexact=affiliate) | Q(employee__department__affiliate__name__iexact=affiliate)
            )
            return base.filter(
                Q(status='hr_approved') |
                Q(status='pending', employee__role='hr') |
                Q(status__in=['ceo_approved', 'approved', 'rejected'])
            ).exclude(employee__role='admin')
        elif aff_ilike in ['sdsl', 'sbl']:
            # SDSL/SBL CEO: first approver; sees pending staff (exclude own requests), plus ceo_approved history
            base = qs.filter(
                Q(employee__affiliate__name__iexact=affiliate) | Q(employee__department__affiliate__name__iexact=affiliate)
            ).exclude(employee=user)  # CEO's own requests go to HR
            return base.filter(
                Q(status='pending') | Q(status__in=['ceo_approved', 'approved', 'rejected'])
            ).exclude(employee__role='admin')
        return LeaveRequest.objects.none()

    def _filter_approvable(self, qs):
        user = self.request.user
        approvable = []
        for req in qs:
            handler = ApprovalWorkflowService.get_handler(req)
            if handler.can_approve(user, req.status):
                approvable.append(req)
        return approvable

    @action(detail=False, methods=['get'], url_path='approvals_categorized')
    def approvals_categorized(self, request):
        """Return categorized approvals specific to this CEO."""
        base_qs = self.get_queryset()
        # Only include candidate statuses for action (Merban: hr_approved/pending HR; SDSL/SBL: pending)
        candidate_qs = base_qs.filter(status__in=['pending', 'hr_approved'])
        filtered = self._filter_approvable(candidate_qs)
        data = LeaveRequestListSerializer(filtered, many=True).data
        categorized = {'hod_manager': [], 'hr': [], 'staff': []}
        for item in data:
            role = item.get('employee_role')
            if role == 'manager':
                categorized['hod_manager'].append(item)
            elif role == 'hr':
                categorized['hr'].append(item)
            else:
                categorized['staff'].append(item)
        return Response({
            'categories': categorized,
            'total_count': len(data),
            'counts': {k: len(v) for k, v in categorized.items()},
            'ceo_affiliate': getattr(getattr(request.user, 'affiliate', None), 'name', None)
        })

    @action(detail=False, methods=['get'], url_path='approvals_debug')
    def approvals_debug(self, request):
        qs = self.get_queryset()
        candidate_qs = qs.filter(status__in=['pending', 'hr_approved'])
        debug_items = []
        for req in candidate_qs:
            handler = ApprovalWorkflowService.get_handler(req)
            can = handler.can_approve(request.user, req.status)
            emp = req.employee
            debug_items.append({
                'id': req.id,
                'status': req.status,
                'employee_username': emp.username,
                'employee_email': emp.email,
                'employee_role': getattr(emp, 'role', None),
                'employee_affiliate': getattr(getattr(emp, 'affiliate', None), 'name', None),
                'department_affiliate': getattr(getattr(getattr(emp, 'department', None), 'affiliate', None), 'name', None),
                'can_approve': can,
                'handler': handler.__class__.__name__,
            })
        return Response({
            'user': {
                'id': request.user.id,
                'affiliate': getattr(getattr(request.user, 'affiliate', None), 'name', None),
            },
            'candidate_ids': [r.id for r in candidate_qs],
            'approvable_ids': [d['id'] for d in debug_items if d['can_approve']],
            'debug': debug_items,
        })

    @action(detail=False, methods=['get'], url_path='recent_activity')
    def recent_activity(self, request):
        """Recent items where this CEO acted (ceo_approved_by)."""
        try:
            limit = int(request.query_params.get('limit', 15))
        except Exception:
            limit = 15
        qs = LeaveRequest.objects.filter(ceo_approved_by=request.user).order_by('-ceo_approval_date', '-updated_at')[:limit]
        data = LeaveRequestListSerializer(qs, many=True).data
        return Response({'count': len(data), 'results': data})

    @action(detail=True, methods=['put'], url_path='approve')
    def approve(self, request, pk=None):
        try:
            lr = LeaveRequest.objects.get(pk=pk)
        except LeaveRequest.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        if lr not in self._filter_approvable([lr]):
            return Response({'error': 'Not approvable at this stage'}, status=status.HTTP_403_FORBIDDEN)
        comments = request.data.get('approval_comments', '')
        ApprovalWorkflowService.approve_request(lr, request.user, comments)
        return Response({'message': 'Approved', 'new_status': lr.status})

    @action(detail=True, methods=['put'], url_path='reject')
    def reject(self, request, pk=None):
        try:
            lr = LeaveRequest.objects.get(pk=pk)
        except LeaveRequest.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        # Allow rejection if CEO could approve or if status in a CEO-visible stage
        if lr.status not in ['pending', 'hr_approved', 'ceo_approved']:
            return Response({'error': 'Cannot reject at this stage'}, status=status.HTTP_403_FORBIDDEN)
        comments = request.data.get('rejection_comments') or request.data.get('approval_comments') or ''
        lr.reject(request.user, comments, 'ceo')
        return Response({'message': 'Rejected', 'new_status': lr.status})
