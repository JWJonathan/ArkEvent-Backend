from rest_framework import serializers
from .models import EventView, EventAnalyticsDaily, ActivityLog

class EventViewSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')
    user_name = serializers.ReadOnlyField(source='user.full_name')

    class Meta:
        model = EventView
        fields = ['id', 'event_id', 'event_title', 'user_id', 'user_name', 'source', 'viewed_at']
        read_only_fields = ['id', 'viewed_at']

class EventAnalyticsDailySerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')

    class Meta:
        model = EventAnalyticsDaily
        fields = [
            'id', 'event_id', 'event_title', 'date', 'views', 'unique_views',
            'shares', 'orders', 'tickets_sold', 'revenue', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.full_name')

    class Meta:
        model = ActivityLog
        fields = [
            'id', 'user_id', 'user_name', 'action', 'entity_type', 'entity_id',
            'ip_address', 'user_agent', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']