"""
Subscription Service Layer
Handles subscription plans, billing, and user subscriptions.
"""

from decimal import Decimal
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone

from .models import SubscriptionPlan, UserSubscription, PremiumFeature, UserPremiumFeature
from apps.wallets.models import Wallet
from apps.wallets.services import WalletService


class SubscriptionService:
    """Manages user subscriptions to plans."""
    
    @staticmethod
    def get_active_subscription(user) -> UserSubscription or None:
        """Get user's active subscription."""
        return UserSubscription.objects.filter(
            user=user,
            status='active'
        ).first()
    
    @staticmethod
    def get_subscription_tier(user) -> str:
        """Get subscription tier for user (free if no subscription)."""
        subscription = SubscriptionService.get_active_subscription(user)
        if subscription:
            return subscription.plan.tier
        return 'free'
    
    @staticmethod
    @transaction.atomic
    def subscribe_user(
        user,
        plan: SubscriptionPlan,
        payment_method = None,
        currency: str = 'USD'
    ) -> UserSubscription:
        """
        Subscribe user to plan.
        Creates subscription and charges payment method if applicable.
        """
        # Cancel existing subscription if any
        existing = UserSubscription.objects.filter(user=user, status='active').first()
        if existing:
            SubscriptionService.cancel_subscription(existing)
        
        # Calculate billing dates
        start_date = timezone.now().date()
        if plan.billing_cycle == 'monthly':
            renewal_date = start_date + timedelta(days=30)
        else:  # annual
            renewal_date = start_date + timedelta(days=365)
        
        # Get amount for currency
        if currency == 'USD':
            amount = plan.price_usd
        else:
            amount = plan.price_htg
        
        # Create subscription
        subscription = UserSubscription.objects.create(
            user=user,
            plan=plan,
            status='active',
            start_date=start_date,
            renewal_date=renewal_date,
            auto_renew=True,
            payment_method=payment_method,
            amount_paid=amount,
            currency=currency
        )
        
        from apps.notifications.services import NotificationService
        NotificationService.notify_payment_user(user, 'success', amount, currency)
        
        return subscription
    
    @staticmethod
    @transaction.atomic
    def renew_subscription(subscription: UserSubscription):
        """
        Renew user's subscription.
        Charges payment method again.
        """
        plan = subscription.plan
        user = subscription.user
        
        # Update dates
        old_renewal = subscription.renewal_date
        if plan.billing_cycle == 'monthly':
            new_renewal = old_renewal + timedelta(days=30)
        else:
            new_renewal = old_renewal + timedelta(days=365)
        
        subscription.renewal_date = new_renewal
        subscription.save(update_fields=['renewal_date'])
        
        from apps.notifications.services import NotificationService
        NotificationService.notify_payment_user(user, 'sub_renewed')
        
        return subscription
    
    @staticmethod
    def cancel_subscription(subscription: UserSubscription):
        """Cancel user's subscription."""
        subscription.status = 'cancelled'
        subscription.cancelled_at = timezone.now()
        subscription.save(update_fields=['status', 'cancelled_at', 'updated_at'])
    
    @staticmethod
    def pause_subscription(subscription: UserSubscription):
        """Pause user's subscription."""
        subscription.status = 'paused'
        subscription.save(update_fields=['status', 'updated_at'])
    
    @staticmethod
    def resume_subscription(subscription: UserSubscription):
        """Resume paused subscription."""
        subscription.status = 'active'
        subscription.save(update_fields=['status', 'updated_at'])

    @staticmethod
    def is_subscription_active(user) -> bool:
        """Check if user has active subscription."""
        return UserSubscription.objects.filter(
            user=user,
            status='active',
            renewal_date__gt=timezone.now().date()
        ).exists()
    
    @staticmethod
    def get_subscription_features(user) -> dict:
        """Get features available to user based on subscription."""
        subscription = SubscriptionService.get_active_subscription(user)
        
        if not subscription:
            plan = SubscriptionPlan.objects.get(tier='free')
        else:
            plan = subscription.plan
        
        return {
            'tier': plan.tier,
            'max_active_events': plan.max_active_events,
            'max_tickets_per_event': plan.max_tickets_per_event,
            'commission_percentage': plan.commission_percentage,
            'requires_branding': plan.requires_branding,
            'has_qr_checkin': plan.has_qr_checkin,
            'has_basic_analytics': plan.has_basic_analytics,
            'has_advanced_analytics': plan.has_advanced_analytics,
            'has_custom_pages': plan.has_custom_pages,
            'has_marketing_tools': plan.has_marketing_tools,
            'has_multi_admin': plan.has_multi_admin,
            'has_api_access': plan.has_api_access,
            'has_custom_domain': plan.has_custom_domain,
            'has_white_label': plan.has_white_label,
            'has_sponsor_placement': plan.has_sponsor_placement,
            'priority_support_level': plan.priority_support_level,
        }
    
    @staticmethod
    def get_user_subscription_history(user):
        """Get user's subscription history."""
        return UserSubscription.objects.filter(user=user).order_by('-start_date')
    
    @staticmethod
    def is_user_eligible_for_plan(user, plan: SubscriptionPlan) -> bool:
        """Check if user is eligible to subscribe to a plan."""
        # For example, free plan is always eligible
        if plan.tier == 'free':
            return True
            
        # Anonymous users are not eligible for non-free plans
        if user.is_anonymous:
            return False
        
        # Check if user already has an active subscription to the same or higher tier
        active = SubscriptionService.get_active_subscription(user)
        if active and active.plan.tier in ['pro', 'enterprise']:
            return False
        
        return True
    
    @staticmethod
    def get_plan_features(plan: SubscriptionPlan) -> dict:
        """Get features of a subscription plan."""
        return {
            'tier': plan.tier,
            'max_active_events': plan.max_active_events,
            'max_tickets_per_event': plan.max_tickets_per_event,
            'commission_percentage': plan.commission_percentage,
            'requires_branding': plan.requires_branding,
            'has_qr_checkin': plan.has_qr_checkin,
            'has_basic_analytics': plan.has_basic_analytics,
            'has_advanced_analytics': plan.has_advanced_analytics,
            'has_custom_pages': plan.has_custom_pages,
            'has_marketing_tools': plan.has_marketing_tools,
            'has_multi_admin': plan.has_multi_admin,
            'has_api_access': plan.has_api_access,
            'has_custom_domain': plan.has_custom_domain,
            'has_white_label': plan.has_white_label,
            'has_sponsor_placement': plan.has_sponsor_placement,
            'priority_support_level': plan.priority_support_level,
        }
    
    @staticmethod
    def get_plan_pricing(plan: SubscriptionPlan) -> dict:
        """Get pricing details of a subscription plan."""
        return {
            'price_htg': plan.price_htg,
            'price_usd': plan.price_usd,
            'billing_cycle': plan.billing_cycle,
        }
    


class PremiumFeatureService:
    """Manages premium feature purchases."""
    
    @staticmethod
    @transaction.atomic
    def purchase_premium_feature(
        user,
        feature: PremiumFeature,
        event = None,
        currency: str = 'USD',
        transaction_id: str = None
    ) -> UserPremiumFeature:
        """
        Purchase premium feature.
        Debits wallet and creates premium feature record.
        """
        # Get or create wallet
        wallet = WalletService.get_or_create_wallet(user)
        
        # Get price for currency
        if currency == 'USD':
            price = feature.price_usd
        else:
            price = feature.price_htg
        
        # Validate balance
        if wallet.available_balance < price:
            raise ValueError(
                f"Insufficient balance. Available: {wallet.available_balance}, "
                f"Required: {price}"
            )
        
        # Debit wallet
        WalletService.debit_wallet(
            wallet,
            price,
            'premium_feature_charge',
            f"Premium feature: {feature.get_feature_type_display()}",
            str(transaction_id) if transaction_id else ''
        )
        
        # Calculate expiration
        if feature.duration_unit == 'days':
            expires_at = timezone.now() + timedelta(days=feature.duration)
        elif feature.duration_unit == 'months':
            expires_at = timezone.now() + timedelta(days=feature.duration * 30)
        else:  # years
            expires_at = timezone.now() + timedelta(days=feature.duration * 365)
        
        # Create premium feature record
        user_premium = UserPremiumFeature.objects.create(
            user=user,
            feature=feature,
            event=event,
            amount_paid=price,
            currency=currency,
            expires_at=expires_at,
            transaction_id=transaction_id,
            is_active=True
        )
        
        return user_premium
    
    @staticmethod
    def get_active_premium_features(user, event=None):
        """Get user's active premium features."""
        query = UserPremiumFeature.objects.filter(
            user=user,
            is_active=True,
            expires_at__gt=timezone.now()
        )
        
        if event:
            query = query.filter(event=event)
        
        return query
    
    @staticmethod
    def has_premium_feature(user, feature_type: str, event=None) -> bool:
        """Check if user has specific premium feature active."""
        query = UserPremiumFeature.objects.filter(
            user=user,
            feature__feature_type=feature_type,
            is_active=True,
            expires_at__gt=timezone.now()
        )
        
        if event:
            query = query.filter(event=event)
        
        return query.exists()
    
    @staticmethod
    def get_event_boost_analytics(user_premium: UserPremiumFeature):
        """Get analytics for event boost."""
        return {
            'feature': user_premium.feature.get_feature_type_display(),
            'event': user_premium.event,
            'activated_at': user_premium.activated_at,
            'expires_at': user_premium.expires_at,
            'is_active': user_premium.is_active,
            'days_remaining': (user_premium.expires_at - timezone.now()).days,
            'impressions': getattr(user_premium, 'impressions', 0),
            'clicks': getattr(user_premium, 'clicks', 0),
            'conversions': getattr(user_premium, 'conversions', 0),
        }


class SubscriptionAnalyticsService:
    """Analytics for subscriptions."""
    
    @staticmethod
    def get_subscription_stats() -> dict:
        """Get platform subscription statistics."""
        from django.db.models import Count
        
        stats_by_tier = {}
        for plan in SubscriptionPlan.objects.filter(is_active=True):
            count = UserSubscription.objects.filter(
                plan=plan,
                status='active'
            ).count()
            stats_by_tier[plan.tier] = {
                'count': count,
                'price_htg': plan.price_htg,
                'price_usd': plan.price_usd,
                'commission_percentage': plan.commission_percentage,
            }
        
        return stats_by_tier
    
    @staticmethod
    def get_user_subscription_features(user) -> dict:
        """Get all subscription features for user."""
        subscription = SubscriptionService.get_active_subscription(user)
        
        if not subscription:
            plan = SubscriptionPlan.objects.get(tier='free')
        else:
            plan = subscription.plan
        
        return {
            'tier': plan.tier if subscription else 'free',
            'max_active_events': plan.max_active_events,
            'max_tickets_per_event': plan.max_tickets_per_event,
            'commission_percentage': plan.commission_percentage,
            'requires_branding': plan.requires_branding,
            'has_qr_checkin': plan.has_qr_checkin,
            'has_basic_analytics': plan.has_basic_analytics,
            'has_advanced_analytics': plan.has_advanced_analytics,
            'has_custom_pages': plan.has_custom_pages,
            'has_marketing_tools': plan.has_marketing_tools,
            'has_multi_admin': plan.has_multi_admin,
            'has_api_access': plan.has_api_access,
            'has_custom_domain': plan.has_custom_domain,
            'has_white_label': plan.has_white_label,
            'has_sponsor_placement': plan.has_sponsor_placement,
            'priority_support_level': plan.priority_support_level,
        }
