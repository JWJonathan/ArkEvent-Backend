"""
DRF Serializers for Subscriptions
"""

from rest_framework import serializers
from .models import SubscriptionPlan, UserSubscription, PremiumFeature, UserPremiumFeature


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    tier_display = serializers.CharField(source='get_tier_display', read_only=True)
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'tier', 'tier_display', 'price_htg', 'price_usd', 'billing_cycle',
            'max_active_events', 'max_tickets_per_event', 'commission_percentage',
            'requires_branding', 'has_qr_checkin', 'has_basic_analytics',
            'has_advanced_analytics', 'has_custom_pages', 'has_marketing_tools',
            'has_multi_admin', 'has_api_access', 'has_custom_domain', 'has_white_label',
            'has_sponsor_placement', 'priority_support_level', 'is_active', 'description'
        ]
        read_only_fields = ['id']


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan_data = SubscriptionPlanSerializer(source='plan', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='payment_method.display_name', read_only=True, allow_null=True)
    
    class Meta:
        model = UserSubscription
        fields = [
            'id', 'user', 'plan', 'plan_data', 'status', 'status_display',
            'start_date', 'end_date', 'renewal_date', 'auto_renew',
            'payment_method', 'payment_method_display', 'amount_paid', 'currency',
            'purchase_token', 'order_id', 'expiry_date',
            'cancelled_at', 'cancellation_reason', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'start_date', 'created_at', 'updated_at']


class PremiumFeatureSerializer(serializers.ModelSerializer):
    feature_type_display = serializers.CharField(source='get_feature_type_display', read_only=True)
    duration_unit_display = serializers.CharField(source='get_duration_unit_display', read_only=True)
    
    class Meta:
        model = PremiumFeature
        fields = [
            'id', 'feature_type', 'feature_type_display', 'price_htg', 'price_usd',
            'duration', 'duration_unit', 'duration_unit_display', 'description', 'is_active'
        ]
        read_only_fields = ['id']


class UserPremiumFeatureSerializer(serializers.ModelSerializer):
    feature_data = PremiumFeatureSerializer(source='feature', read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True, allow_null=True)
    days_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = UserPremiumFeature
        fields = [
            'id', 'user', 'feature', 'feature_data', 'event', 'event_title',
            'amount_paid', 'currency', 'activated_at', 'expires_at', 'is_active',
            'transaction_id', 'days_remaining'
        ]
        read_only_fields = ['id', 'user', 'activated_at', 'transaction_id']
    
    def get_days_remaining(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        
        remaining = obj.expires_at - timezone.now()
        if remaining < timedelta(0):
            return 0
        return remaining.days
