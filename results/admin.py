from django.contrib import admin
from .models import Subject, Result, AuditLog, Notification

admin.site.register(Subject)
admin.site.register(Result)

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('action', 'user__username', 'details')
    readonly_fields = ('user', 'action', 'details', 'created_at')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'message', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('recipient__username', 'message')