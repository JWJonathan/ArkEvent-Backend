from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription, PremiumFeature, UserPremiumFeature

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('tier', 'price_htg', 'price_usd', 'billing_cycle', 'is_active')
    list_filter = ('billing_cycle', 'is_active')
    search_fields = ('tier', 'description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'start_date', 'renewal_date', 'auto_renew')
    list_filter = ('status', 'plan', 'auto_renew', 'start_date', 'renewal_date')
    search_fields = ('user__email', 'user__username', 'user__full_name')
    readonly_fields = ('created_at', 'updated_at', 'cancelled_at')
    raw_id_fields = ('user', 'plan', 'payment_method')
    ordering = ('-created_at',)

@admin.register(PremiumFeature)
class PremiumFeatureAdmin(admin.ModelAdmin):
    list_display = ('feature_type', 'price_htg', 'price_usd', 'duration', 'duration_unit', 'is_active')
    list_filter = ('feature_type', 'duration_unit', 'is_active')
    search_fields = ('feature_type', 'description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(UserPremiumFeature)
class UserPremiumFeatureAdmin(admin.ModelAdmin):
    list_display = ('user', 'feature', 'event', 'amount_paid', 'currency', 'is_active', 'expires_at')
    list_filter = ('is_active', 'currency', 'feature', 'expires_at')
    search_fields = ('user__email', 'feature__feature_type', 'event__title', 'transaction_id')
    readonly_fields = ('activated_at',)
    raw_id_fields = ('user', 'feature', 'event')
    ordering = ('-activated_at',)
