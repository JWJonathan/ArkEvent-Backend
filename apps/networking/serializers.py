from rest_framework import serializers
from .models import NetworkingMatch, SocialPost

class NetworkingMatchSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')
    user1_name = serializers.ReadOnlyField(source='user1.profile.full_name')
    user2_name = serializers.ReadOnlyField(source='user2.profile.full_name')

    class Meta:
        model = NetworkingMatch
        fields = [
            'id', 'event_id', 'event_title', 'user1_id', 'user1_name',
            'user2_id', 'user2_name', 'status', 'matched_at'
        ]
        read_only_fields = ['id', 'matched_at']

class SocialPostSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')
    creator_name = serializers.ReadOnlyField(source='created_by.profile.full_name')

    class Meta:
        model = SocialPost
        fields = [
            'id', 'event_id', 'event_title', 'platform', 'content',
            'image', 'scheduled_at', 'posted_at', 'status',
            'created_by', 'creator_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        