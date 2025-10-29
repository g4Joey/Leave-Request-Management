from django.contrib import admin
from .models import CustomUser, Department


# EmploymentGrade removed from admin (deprecated)


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
	list_display = (
		'username', 'email', 'first_name', 'last_name', 'role', 'department', 'is_active'
	)
	list_filter = ('role', 'department', 'is_active', 'is_staff')
	search_fields = ('username', 'email', 'first_name', 'last_name', 'employee_id')
	autocomplete_fields = ('department',)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name', 'description')# Register your models here.
