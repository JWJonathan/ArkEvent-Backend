"""
DRF Serializers for Finance
"""

from rest_framework import serializers
from .models import PlatformRevenue, RevenueReport, EventBoost, AnalyticsDailyMetric


class PlatformRevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformRevenue
        fields = [
            'id', 'revenue_date', 'revenue_month', 'ticket_commission_revenue',
            'subscription_revenue', 'premium_feature_revenue', 'event_boost_revenue',
            'total_revenue', 'currency', 'ticket_sales_count', 'new_subscriptions_count',
            'premium_features_purchased_count', 'created_at', 'updated_at'
        ]
        read_only_fields = fields


class RevenueReportSerializer(serializers.ModelSerializer):
    organizer_name = serializers.CharField(source='organizer.name', read_only=True)
    top_event_title = serializers.CharField(source='top_event.title', read_only=True, allow_null=True)
    period_type_display = serializers.CharField(source='get_period_type_display', read_only=True)
    
    class Meta:
        model = RevenueReport
        fields = [
            'id', 'organizer', 'organizer_name', 'period_type', 'period_type_display',
            'start_date', 'end_date', 'gross_revenue', 'total_commissions', 'net_revenue',
            'currency', 'total_ticket_sales', 'total_tickets_sold', 'average_ticket_price',
            'events_count', 'top_event', 'top_event_title', 'refunds_count', 'refunds_amount',
            'created_at'
        ]
        read_only_fields = fields


class EventBoostSerializer(serializers.ModelSerializer):
    boost_type_display = serializers.CharField(source='get_boost_type_display', read_only=True)
    duration_display = serializers.CharField(source='get_duration_display', read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)
    paid_by_name = serializers.CharField(source='paid_by.get_full_name', read_only=True)
    days_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = EventBoost
        fields = [
            'id', 'event', 'event_title', 'boost_type', 'boost_type_display',
            'duration', 'duration_display', 'cost_htg', 'cost_usd', 'paid_by',
            'paid_by_name', 'activated_at', 'expires_at', 'is_active',
            'impressions', 'clicks', 'conversions', 'days_remaining', 'created_at'
        ]
        read_only_fields = fields
    
    def get_days_remaining(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        
        remaining = obj.expires_at - timezone.now()
        if remaining < timedelta(0):
            return 0
        return remaining.days


class AnalyticsDailyMetricSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    
    class Meta:
        model = AnalyticsDailyMetric
        fields = [
            'id', 'event', 'event_title', 'metric_date', 'page_views',
            'unique_visitors', 'tickets_sold', 'revenue', 'currency',
            'refunds', 'refund_amount', 'created_at'
        ]
        read_only_fields = fields
