from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LeaveRequestViewSet,
    LeaveBalanceViewSet,
    LeaveTypeViewSet,
    ManagerLeaveViewSet,
    EmploymentGradeViewSet,
    LeaveGradeEntitlementViewSet,
    export_all_proxy,
)
from .role_views import RoleEntitlementViewSet
from .approval_dashboard import approval_dashboard
from .views_overlap import OverlapAPIView, OverlapSummaryAPIView

router = DefaultRouter()
router.register(r'requests', LeaveRequestViewSet, basename='leave-requests')
router.register(r'balances', LeaveBalanceViewSet, basename='leave-balances')
router.register(r'types', LeaveTypeViewSet, basename='leave-types')
router.register(r'manager', ManagerLeaveViewSet, basename='manager-leaves')
router.register(r'role-entitlements', RoleEntitlementViewSet, basename='role-entitlements')

urlpatterns = [
    # Explicit non-ambiguous export endpoint for leave requests (list-action).
    # This avoids DRF router ambiguity where a segment like 'export_all' can be
    # interpreted as a {pk} detail route. The viewset method `export_all` will
    # handle permissions and CSV generation.
    # Stable proxy endpoints for exporting all leave requests as CSV
    path('requests/export_all_list/', export_all_proxy, name='leave-requests-export-all-list'),
    path('requests/export-all-list/', export_all_proxy, name='leave-requests-export-all-list-hyphen'),
    path('', include(router.urls)),
    path('approval-dashboard/', approval_dashboard, name='approval-dashboard'),
    path('overlaps/', OverlapAPIView.as_view(), name='leave-overlaps'),
    path('overlaps/summary/', OverlapSummaryAPIView.as_view(), name='leave-overlaps-summary'),
]