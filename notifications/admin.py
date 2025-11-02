from django.contrib import admin
from .models import Notification, EmailTemplate, SiteSetting

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
	list_display = ("title", "recipient", "notification_type", "created_at", "is_read")
	list_filter = ("notification_type", "is_read", "created_at")
	search_fields = ("title", "message", "recipient__username", "recipient__email")

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
	list_display = ("notification_type", "subject_template", "is_active")
	list_filter = ("is_active",)
	search_fields = ("notification_type", "subject_template")

@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
	list_display = ("key", "value", "updated_at")
	search_fields = ("key", "value")
