from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, UserProfileView, StaffManagementView, MyProfileView, DepartmentViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'departments', DepartmentViewSet, basename='department')

urlpatterns = [
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('me/', MyProfileView.as_view(), name='my-profile'),
    path('staff/', StaffManagementView.as_view(), name='staff-management'),
    path('', include(router.urls)),
]