from django.contrib import admin
from .models import CustomUser, EmploymentGrade, Department


@admin.register(EmploymentGrade)
class EmploymentGradeAdmin(admin.ModelAdmin):
	list_display = ('name', 'slug', 'is_active', 'created_at')
	list_filter = ('is_active',)
	search_fields = ('name', 'slug')
	prepopulated_fields = {"slug": ("name",)}


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
	list_display = (
		'username', 'email', 'first_name', 'last_name', 'role', 'department', 'grade', 'is_active'
	)
	list_filter = ('role', 'department', 'grade', 'is_active', 'is_staff')
	search_fields = ('username', 'email', 'first_name', 'last_name', 'employee_id')
	autocomplete_fields = ('department', 'grade')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name', 'description')# Register your models here.
