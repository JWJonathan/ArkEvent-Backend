from rest_framework import serializers
from .models import EmailCampaign, EmailSubscriber

class EmailCampaignSerializer(serializers.ModelSerializer):
    organization_name = serializers.ReadOnlyField(source='organization.name')
    event_title = serializers.ReadOnlyField(source='event.title')

    class Meta:
        model = EmailCampaign
        fields = [
            'id', 'organization_id', 'organization_name', 'event_id', 'event_title',
            'subject', 'body_html', 'body_text', 'sender_name', 'sender_email',
            'status', 'scheduled_for', 'sent_at', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class EmailSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailSubscriber
        fields = ['id', 'email', 'name', 'is_active', 'subscribed_at', 'unsubscribed_at', 'source', 'metadata']
        read_only_fields = ['id', 'subscribed_at', 'unsubscribed_at']
        