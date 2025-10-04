"""
URL configuration for leave_management project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView
from users.auth import EmailOrUsernameTokenObtainPairView
from . import views
from django.views.generic import RedirectView  # noqa: F401 (kept for potential future use)

urlpatterns = [
    path('api/health/', views.health_check, name='health_check'),
    path('api/health', views.api_health, name='api_health'),
    path('api/health/db', views.api_health_db, name='api_health_db'),
    path('admin/', admin.site.urls),
    path('api/auth/token/', EmailOrUsernameTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/leaves/', include('leaves.urls')),
    path('api/users/', include('users.urls')),
    # Fallback routes without the '/api' prefix. Some platforms may strip the path prefix
    # when forwarding to the backend service. These mirror the API endpoints so requests
    # will still resolve correctly.
    path('health/', views.health_check, name='health_check_root'),
    path('health', views.api_health, name='api_health_root'),
    path('health/db', views.api_health_db, name='api_health_db_root'),
    path('auth/token/', EmailOrUsernameTokenObtainPairView.as_view(), name='token_obtain_pair_root'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh_root'),
    path('leaves/', include('leaves.urls')),
    path('users/', include('users.urls')),
]

# Serve React app (for production)
if not settings.DEBUG:
    from django.views.generic import TemplateView
    from django.urls import re_path
    import os
    
    # Serve React app for all other routes (SPA routing).
    # Exclude API, static, media, and any path that looks like a file
    # (contains a dot) so asset requests are not routed to index.html.
    # Matches only URLs that do NOT start with api/, static/, media/
    # and do NOT contain a dot (e.g. .js, .css, .png).
    urlpatterns += [
        re_path(r'^(?!api/|static/|media/)(?!.*\.).*$', TemplateView.as_view(template_name='index.html'), name='react_app'),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Error handlers
handler404 = 'leave_management.views.not_found'
handler500 = 'leave_management.views.server_error'
