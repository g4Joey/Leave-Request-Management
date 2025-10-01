from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, UserProfileView, StaffManagementView, MyProfileView, DepartmentViewSet, ChangePasswordView

router = DefaultRouter()
"""Router configuration:
Register the user viewset at the root so that including this urls.py at
path('api/users/', ...) yields endpoints:
    /api/users/            -> user list
    /api/users/<pk>/       -> user detail

Previously this was registered as 'users', producing paths like
    /api/users/users/<pk>/ which broke frontend calls to /api/users/<pk>/.
"""
router.register(r'', UserViewSet, basename='user')
router.register(r'departments', DepartmentViewSet, basename='department')

urlpatterns = [
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('me/', MyProfileView.as_view(), name='my-profile'),
    path('me/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('staff/', StaffManagementView.as_view(), name='staff-management'),
    path('', include(router.urls)),
]