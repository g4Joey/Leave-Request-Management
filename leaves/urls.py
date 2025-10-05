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

router = DefaultRouter()
router.register(r'requests', LeaveRequestViewSet, basename='leave-requests')
router.register(r'balances', LeaveBalanceViewSet, basename='leave-balances')
router.register(r'types', LeaveTypeViewSet, basename='leave-types')
router.register(r'manager', ManagerLeaveViewSet, basename='manager-leaves')
router.register(r'grades', EmploymentGradeViewSet, basename='employment-grades')
router.register(r'grade-entitlements', LeaveGradeEntitlementViewSet, basename='grade-entitlements')
router.register(r'role-entitlements', RoleEntitlementViewSet, basename='role-entitlements')

urlpatterns = [
    path('', include(router.urls)),
]