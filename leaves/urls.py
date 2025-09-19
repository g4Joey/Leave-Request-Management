from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LeaveRequestViewSet,
    LeaveBalanceViewSet,
    LeaveTypeViewSet,
    ManagerLeaveViewSet
)

router = DefaultRouter()
router.register(r'requests', LeaveRequestViewSet, basename='leave-requests')
router.register(r'balances', LeaveBalanceViewSet, basename='leave-balances')
router.register(r'types', LeaveTypeViewSet, basename='leave-types')
router.register(r'manager', ManagerLeaveViewSet, basename='manager-leaves')

urlpatterns = [
    path('', include(router.urls)),
]