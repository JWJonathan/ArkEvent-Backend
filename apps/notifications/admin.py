from django.contrib import admin
from .models import NotificationLog, EventNotificationSetting, PushToken, UserDevice

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'type', 'event', 'sent_at', 'read_at')
    list_filter = ('type', 'sent_at', 'event')
    search_fields = ('title', 'body', 'user__email')
    readonly_fields = ('id', 'sent_at')
    raw_id_fields = ('user', 'event', 'order')

@admin.register(EventNotificationSetting)
class EventNotificationSettingAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'push_enabled', 'email_enabled')
    list_filter = ('push_enabled', 'email_enabled', 'event')
    search_fields = ('user__email', 'event__title')
    raw_id_fields = ('user', 'event')

@admin.register(PushToken)
class PushTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'is_active', 'created_at')
    list_filter = ('platform', 'is_active', 'created_at')
    search_fields = ('user__email', 'token')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('user',)

@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_name', 'os', 'app_version', 'last_seen')
    list_filter = ('os', 'last_seen')
    search_fields = ('user__email', 'device_id', 'device_name')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('user',)
