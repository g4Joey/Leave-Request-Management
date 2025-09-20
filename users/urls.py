from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, UserProfileView

router = DefaultRouter()
router.register(r'', UserViewSet)

urlpatterns = [
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('', include(router.urls)),
]