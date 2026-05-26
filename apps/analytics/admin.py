from django.contrib import admin
from .models import EventView, EventAnalyticsDaily, ActivityLog

@admin.register(EventView)
class EventViewAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'source', 'viewed_at')
    list_filter = ('source', 'viewed_at', 'event')
    search_fields = ('event__title', 'user__email', 'source')
    readonly_fields = ('id', 'viewed_at')
    raw_id_fields = ('event', 'user')

@admin.register(EventAnalyticsDaily)
class EventAnalyticsDailyAdmin(admin.ModelAdmin):
    list_display = ('event', 'date', 'views', 'unique_views', 'revenue')
    list_filter = ('date', 'event')
    search_fields = ('event__title',)
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('event',)

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'entity_type', 'ip_address', 'created_at')
    list_filter = ('action', 'entity_type', 'created_at')
    search_fields = ('action', 'user__email', 'entity_id', 'ip_address')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('user',)
