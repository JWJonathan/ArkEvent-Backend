from rest_framework import serializers
from .models import Announcement, Event, EventCategory, EventSession, EventSpeaker, EventOrganizer, EventMedia, EventSponsor, EventFaq, EventShare
from apps.organization.models import Organization

from rest_framework import serializers
from .models import Event

class EventSerializer(serializers.ModelSerializer):
    organization_name = serializers.ReadOnlyField(source='organization.name')
    category_name = serializers.ReadOnlyField(source='category.name')
    created_by_email = serializers.ReadOnlyField(source='created_by.email')
    image_url = serializers.ImageField(source='poster', read_only=True)  # alias pour compatibilité Flutter
    requires_branding = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'organization', 'organization_id', 'organization_name',
            'category_id', 'category_name',
            'created_by', 'created_by_email',
            'title', 'slug', 'short_description', 'description',
            'highlights', 'tags',
            'poster', 'banner', 'thumbnail', 'video', 'image_url',
            'start_date', 'end_date', 'doors_open', 'timezone',
            'venue_name', 'venue_address', 'venue_city', 'venue_state',
            'venue_country', 'venue_postal_code', 'latitude', 'longitude',
            'location_display', 'is_online', 'online_url',
            'capacity', 'age_limit', 'is_free',
            'status', 'visibility',
            'ticket_opens_at', 'ticket_closes_at', 'currency',
            'min_price', 'max_price',
            'marketing_budget', 'expected_attendance', 'target_audience',
            'custom_registration_url', 'meta_title', 'meta_description',
            'meta_keywords', 'structured_data',
            'has_waitlist', 'waitlist_capacity', 'allow_transfers',
            'require_approval', 'checkin_method', 'event_language',
            'accessibility_info', 'sustainability_info',
            'metadata', 'settings',
            'created_at', 'updated_at', 'published_at',
            'requires_branding'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'published_at', 'organization_name', 'category_name', 'created_by_email', 'created_by']

    def get_requires_branding(self, obj):
        from apps.subscriptions.services import SubscriptionService
        features = SubscriptionService.get_subscription_features(obj.created_by)
        return features.get('requires_branding', True)

class EventCategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.ReadOnlyField(source='parent.name')
    children = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = EventCategory
        fields = [
            'id', 'name', 'slug', 'description', 'icon', 'image',
            'parent', 'parent_name', 'children',
            'sort_order', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EventSessionSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')

    class Meta:
        model = EventSession
        fields = [
            'id', 'event_id', 'event_title', 'title', 'description',
            'session_type', 'start_time', 'end_time', 'location',
            'capacity', 'speakers', 'image', 'recording',
            'requires_ticket', 'ticket_type_id', 'sort_order',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EventSpeakerSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')

    class Meta:
        model = EventSpeaker
        fields = [
            'id', 'event', 'event_id', 'event_title', 'profile_id', 'full_name',
            'role', 'bio', 'photo', 'social_links', 'sort_order', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']



class EventOrganizerSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')
    user_name = serializers.ReadOnlyField(source='user.profile.full_name')  # ajustez selon votre modèle utilisateur

    class Meta:
        model = EventOrganizer
        fields = ['id', 'event_id', 'event_title', 'user_id', 'user_name', 'role', 'added_by', 'created_at']
        read_only_fields = ['id', 'created_at']


class EventMediaSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')
    uploader_name = serializers.ReadOnlyField(source='uploaded_by.profile.full_name')

    class Meta:
        model = EventMedia
        fields = [
            'id', 'event_id', 'event_title', 'uploaded_by', 'uploader_name',
            'media_type', 'file', 'alt_text', 'title', 'description',
            'sort_order', 'is_featured', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class EventSponsorSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')

    class Meta:
        model = EventSponsor
        fields = [
            'id', 'event_id', 'event_title', 'name', 'logo',
            'website', 'level', 'description', 'sort_order', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class EventFaqSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')

    class Meta:
        model = EventFaq
        fields = ['id', 'event_id', 'event_title', 'question', 'answer', 'sort_order', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AnnouncementSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')
    sender_name = serializers.ReadOnlyField(source='sender.profile.full_name')

    class Meta:
        model = Announcement
        fields = [
            'id', 'event_id', 'event_title', 'sender_id', 'sender_name',
            'title', 'message', 'urgency', 'is_push', 'sent_at', 'expires_at', 'created_at'
        ]
        read_only_fields = ['id', 'sent_at', 'created_at']

class EventShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventShare
        fields = ['id', 'event_id', 'user_id', 'platform', 'recipient', 'created_at']
        read_only_fields = ['id', 'created_at']


