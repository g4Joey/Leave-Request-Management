from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LeaveRequestViewSet,
    LeaveBalanceViewSet,
    LeaveTypeViewSet,
    ManagerLeaveViewSet,
    EmploymentGradeViewSet,
    LeaveGradeEntitlementViewSet,
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
    path('', include(router.urls)),
    path('approval-dashboard/', approval_dashboard, name='approval-dashboard'),
    path('overlaps/', OverlapAPIView.as_view(), name='leave-overlaps'),
    path('overlaps/summary/', OverlapSummaryAPIView.as_view(), name='leave-overlaps-summary'),
]