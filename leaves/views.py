from django.shortcuts import render

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum
from django.utils import timezone

from .models import LeaveRequest, LeaveType, LeaveBalance
from .serializers import (
    LeaveRequestSerializer, 
    LeaveRequestListSerializer,
    LeaveApprovalSerializer,
    LeaveTypeSerializer, 
    LeaveBalanceSerializer
)


class LeaveTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for leave types - read only for employees
    """
    queryset = LeaveType.objects.filter(is_active=True)
    serializer_class = LeaveTypeSerializer
    permission_classes = [permissions.IsAuthenticated]


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing leave balances - supports requirements R2, R3
    """
    serializer_class = LeaveBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['year', 'leave_type']
    
    def get_queryset(self):
        """Return balances for the current user only"""
        return LeaveBalance.objects.filter(employee=self.request.user)
    
    @action(detail=False, methods=['get'])
    def current_year(self, request):
        """Get leave balances for current year"""
        current_year = timezone.now().year
        balances = self.get_queryset().filter(year=current_year)
        serializer = self.get_serializer(balances, many=True)
        return Response(serializer.data)
    
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
    
    def get_queryset(self):
        """Return leave requests for the current user"""
        return LeaveRequest.objects.filter(employee=self.request.user)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return LeaveRequestListSerializer
        elif self.action in ['approve', 'reject']:
            return LeaveApprovalSerializer
        return LeaveRequestSerializer
    
    def perform_create(self, serializer):
        """Set the employee to current user when creating - supports R1"""
        serializer.save(employee=self.request.user)
    
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
        total_days_taken = sum(req.total_days for req in current_year_requests.filter(status='approved'))
        pending_days = sum(req.total_days for req in current_year_requests.filter(status='pending'))
        
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
    
    def get_queryset(self):
        """Return leave requests that this manager can approve"""
        user = self.request.user
        
        # For now, managers can see all requests
        # This can be enhanced with proper hierarchy later
        if getattr(user, 'is_superuser', False) or (hasattr(user, 'role') and user.role in ['manager', 'hr', 'admin']):
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
        """Get all pending leave requests for approval"""
        pending_requests = self.get_queryset().filter(status='pending')
        serializer = self.get_serializer(pending_requests, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['put'])
    def approve(self, request, pk=None):
        """Approve a leave request - supports R4"""
        leave_request = self.get_object()
        
        if leave_request.status != 'pending':
            return Response(
                {'error': 'Only pending requests can be approved'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = LeaveApprovalSerializer(
            leave_request, 
            data={'status': 'approved', 'approval_comments': request.data.get('approval_comments', '')},
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Update leave balance
            self._update_leave_balance(leave_request, 'approve')
            
            return Response({'message': 'Leave request approved successfully'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['put'])
    def reject(self, request, pk=None):
        """Reject a leave request - supports R4"""
        leave_request = self.get_object()
        
        if leave_request.status != 'pending':
            return Response(
                {'error': 'Only pending requests can be rejected'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = LeaveApprovalSerializer(
            leave_request,
            data={'status': 'rejected', 'approval_comments': request.data.get('approval_comments', '')},
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Update leave balance (remove from pending)
            self._update_leave_balance(leave_request, 'reject')
            
            return Response({'message': 'Leave request rejected'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _update_leave_balance(self, leave_request, action):
        """Update leave balance based on approval/rejection"""
        try:
            balance = LeaveBalance.objects.get(
                employee=leave_request.employee,
                leave_type=leave_request.leave_type,
                year=leave_request.start_date.year
            )
            
            if action == 'approve':
                # Move from pending to used
                balance.pending_days -= leave_request.total_days
                balance.used_days += leave_request.total_days
            elif action == 'reject':
                # Remove from pending
                balance.pending_days -= leave_request.total_days
            
            balance.save()
            
        except LeaveBalance.DoesNotExist:
            # Handle case where balance doesn't exist
            pass


class IsManagerPermission(permissions.BasePermission):
    """
    Custom permission to only allow managers to approve/reject leaves
    """
    def has_permission(self, request, view):
        user = request.user
        return getattr(user, 'is_superuser', False) or (hasattr(user, 'role') and user.role in ['manager', 'hr', 'admin'])
