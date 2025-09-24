from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, UserProfileView, StaffManagementView, MyProfileView

router = DefaultRouter()
router.register(r'', UserViewSet)

urlpatterns = [
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('me/', MyProfileView.as_view(), name='my-profile'),
    path('staff/', StaffManagementView.as_view(), name='staff-management'),
    path('', include(router.urls)),
]