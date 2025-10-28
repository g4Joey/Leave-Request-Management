from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, UserProfileView, StaffManagementView, MyProfileView, 
    DepartmentViewSet, ChangePasswordView, AdminResetPasswordView, 
    AdminUpdateEmailView, get_role_choices, role_summary, 
    AffiliateViewSet, normalize_merban
)

router = DefaultRouter()
"""Router configuration:
Order matters. Register specific prefixes FIRST (affiliates, departments)
before the catch-all '' user routes. Otherwise, the '' detail route would
match '/api/users/affiliates/' as a user detail (pk='affiliates'), causing
404/405 errors and breaking POST to create affiliates.

Including this urls.py at path('api/users/', ...) yields endpoints:
    /api/users/affiliates/        -> affiliates list/create
    /api/users/affiliates/<pk>/   -> affiliate detail
    /api/users/departments/       -> departments list/create
    /api/users/departments/<pk>/  -> department detail
    /api/users/                   -> user list
    /api/users/<pk>/              -> user detail
"""
router.register(r'affiliates', AffiliateViewSet, basename='affiliate')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('me/', MyProfileView.as_view(), name='my-profile'),
    path('me/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('<int:user_id>/reset-password/', AdminResetPasswordView.as_view(), name='admin-reset-password'),
    path('<int:user_id>/update-email/', AdminUpdateEmailView.as_view(), name='admin-update-email'),
    path('staff/', StaffManagementView.as_view(), name='staff-management'),
    path('admin/normalize-merban/', normalize_merban, name='normalize-merban'),
    path('role-choices/', get_role_choices, name='role-choices'),
    path('role-summary/', role_summary, name='role-summary'),
    path('', include(router.urls)),
]