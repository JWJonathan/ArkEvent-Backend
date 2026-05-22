from rest_framework import serializers
from .models import NotificationLog, EventNotificationSetting, PushToken

class NotificationLogSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.profile.full_name')  # adaptez si votre champ est différent
    event_title = serializers.ReadOnlyField(source='event.title')

    class Meta:
        model = NotificationLog
        fields = [
            'id', 'user_id', 'user_name', 'type', 'title', 'body',
            'event_id', 'event_title', 'order_id', 'metadata',
            'sent_at', 'read_at'
        ]
        read_only_fields = ['id', 'sent_at']


class EventNotificationSettingSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.profile.full_name')
    event_title = serializers.ReadOnlyField(source='event.title')

    class Meta:
        model = EventNotificationSetting
        fields = [
            'id', 'user_id', 'user_name', 'event_id', 'event_title',
            'push_enabled', 'email_enabled'
        ]
        read_only_fields = ['id']


class PushTokenSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.profile.full_name')

    class Meta:
        model = PushToken
        fields = [
            'id', 'user_id', 'user_name', 'token', 'platform',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']