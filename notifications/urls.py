from django.urls import path
from .views_settings import OverlapSettingsAPIView

urlpatterns = [
    path('settings/overlap/', OverlapSettingsAPIView.as_view(), name='overlap-settings'),
]
