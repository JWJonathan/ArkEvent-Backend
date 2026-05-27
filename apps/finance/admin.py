from django.contrib import admin
from .models import PlatformRevenue, RevenueReport, EventBoost, AnalyticsDailyMetric

@admin.register(PlatformRevenue)
class PlatformRevenueAdmin(admin.ModelAdmin):
    list_display = ('revenue_date', 'total_revenue', 'currency', 'ticket_sales_count', 'new_subscriptions_count')
    list_filter = ('currency', 'revenue_date')
    search_fields = ('revenue_date',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-revenue_date',)

@admin.register(RevenueReport)
class RevenueReportAdmin(admin.ModelAdmin):
    list_display = ('organizer', 'period_type', 'start_date', 'end_date', 'net_revenue', 'currency')
    list_filter = ('period_type', 'currency', 'start_date')
    search_fields = ('organizer__name', 'start_date', 'end_date')
    readonly_fields = ('created_at',)
    raw_id_fields = ('organizer', 'top_event')
    ordering = ('-start_date',)

@admin.register(EventBoost)
class EventBoostAdmin(admin.ModelAdmin):
    list_display = ('event', 'boost_type', 'duration', 'is_active', 'activated_at', 'expires_at')
    list_filter = ('boost_type', 'is_active', 'activated_at', 'expires_at')
    search_fields = ('event__title', 'paid_by__email')
    readonly_fields = ('created_at',)
    raw_id_fields = ('event', 'paid_by')
    ordering = ('-activated_at',)

@admin.register(AnalyticsDailyMetric)
class AnalyticsDailyMetricAdmin(admin.ModelAdmin):
    list_display = ('event', 'metric_date', 'page_views', 'tickets_sold', 'revenue', 'currency')
    list_filter = ('metric_date', 'currency', 'event')
    search_fields = ('event__title', 'metric_date')
    readonly_fields = ('created_at',)
    raw_id_fields = ('event',)
    ordering = ('-metric_date',)
