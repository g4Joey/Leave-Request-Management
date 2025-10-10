"""
API endpoint to show approval workflow dashboard
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from leaves.models import LeaveRequest
from leaves.serializers import LeaveRequestSerializer

User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def approval_dashboard(request):
    """
    Dashboard showing leave requests by approval stage
    """
    user = request.user
    user_role = getattr(user, 'role', None)
    
    # Get counts for each approval stage
    pending_manager = LeaveRequest.objects.filter(status='pending').count()
    pending_hr = LeaveRequest.objects.filter(status='manager_approved').count()
    pending_ceo = LeaveRequest.objects.filter(status='hr_approved').count()
    approved = LeaveRequest.objects.filter(status='approved').count()
    rejected = LeaveRequest.objects.filter(status='rejected').count()
    
    # Get requests specific to user's role
    my_pending = []
    if user_role == 'manager':
        my_pending_qs = LeaveRequest.objects.filter(status='pending')
        my_pending = LeaveRequestSerializer(my_pending_qs, many=True).data
    elif user_role == 'hr':
        my_pending_qs = LeaveRequest.objects.filter(status='manager_approved')
        my_pending = LeaveRequestSerializer(my_pending_qs, many=True).data
    elif user_role == 'ceo':
        my_pending_qs = LeaveRequest.objects.filter(status='hr_approved')
        my_pending = LeaveRequestSerializer(my_pending_qs, many=True).data
    elif user_role == 'admin':
        my_pending_qs = LeaveRequest.objects.filter(
            status__in=['pending', 'manager_approved', 'hr_approved']
        )
        my_pending = LeaveRequestSerializer(my_pending_qs, many=True).data
    
    # Get recent activity (last 10 requests)
    recent_activity = LeaveRequest.objects.all()[:10]
    recent_activity_data = LeaveRequestSerializer(recent_activity, many=True).data
    
    return Response({
        'user': {
            'username': user.username,
            'role': user_role,
            'full_name': user.get_full_name(),
        },
        'approval_stages': {
            'pending_manager_approval': pending_manager,
            'pending_hr_approval': pending_hr,
            'pending_ceo_approval': pending_ceo,
            'fully_approved': approved,
            'rejected': rejected
        },
        'my_pending_approvals': {
            'count': len(my_pending),
            'requests': my_pending
        },
        'recent_activity': recent_activity_data,
        'workflow_info': {
            'stages': [
                {'stage': 'manager', 'description': 'Manager Approval', 'order': 1},
                {'stage': 'hr', 'description': 'HR Review', 'order': 2},
                {'stage': 'ceo', 'description': 'CEO Final Approval', 'order': 3}
            ],
            'current_user_stage': {
                'manager': 'You approve requests at Stage 1',
                'hr': 'You approve requests at Stage 2',
                'ceo': 'You give final approval at Stage 3',
                'admin': 'You can approve at any stage'
            }.get(user_role, 'You cannot approve requests')
        }
    })