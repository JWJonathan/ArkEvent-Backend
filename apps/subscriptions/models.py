from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class SubscriptionPlan(models.Model):
    """
    Predefined subscription tier plans.
    FREE, PRO, and BUSINESS tiers with different features and commission rates.
    """
    TIER_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('business', 'Business'),
    ]
    
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, unique=True)
    
    # Pricing in both currencies
    price_htg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Price in HTG"
    )
    price_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Price in USD"
    )
    
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='monthly')
    
    # Features and limits
    max_active_events = models.IntegerField(null=True, blank=True, help_text="NULL = unlimited")
    max_tickets_per_event = models.IntegerField(null=True, blank=True, help_text="NULL = unlimited")
    
    commission_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    requires_branding = models.BooleanField(default=True, help_text="Must show ArkEvent branding")
    has_qr_checkin = models.BooleanField(default=False)
    has_basic_analytics = models.BooleanField(default=True)
    has_advanced_analytics = models.BooleanField(default=False)
    has_custom_pages = models.BooleanField(default=False)
    has_marketing_tools = models.BooleanField(default=False)
    has_multi_admin = models.BooleanField(default=False)
    has_api_access = models.BooleanField(default=False)
    has_custom_domain = models.BooleanField(default=False)
    has_white_label = models.BooleanField(default=False)
    has_sponsor_placement = models.BooleanField(default=False)
    
    priority_support_level = models.CharField(
        max_length=20,
        choices=[
            ('none', 'No Support'),
            ('basic', 'Email Support'),
            ('priority', 'Priority Support'),
            ('dedicated', 'Dedicated Support'),
        ],
        default='none'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent"."subscription_plans'
        ordering = ['tier']

    def __str__(self):
        return f"{self.get_tier_display()} Plan"


class UserSubscription(models.Model):
    """
    Tracks individual user subscriptions to plans.
    Handles subscription lifecycle: active, paused, cancelled.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Subscription dates
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    renewal_date = models.DateField()
    
    # Payment tracking
    auto_renew = models.BooleanField(default=True)
    payment_method = models.ForeignKey(
        'payments.PaymentMethod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Subscription metadata
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='HTG')
    
    # Cancellation info
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent"."user_subscriptions'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.user} - {self.plan.get_tier_display()}"


class PremiumFeature(models.Model):
    """
    Individual premium features that can be purchased by users.
    Examples: Event Boost, Custom Branding, Sponsored Ads.
    """
    FEATURE_TYPE_CHOICES = [
        ('event_boost', 'Event Boost'),
        ('custom_branding', 'Custom Branding'),
        ('sponsored_ads', 'Sponsored Ads'),
        ('api_addon', 'API Add-on'),
        ('priority_support', 'Priority Support'),
    ]
    
    DURATION_UNIT_CHOICES = [
        ('days', 'Days'),
        ('months', 'Months'),
        ('years', 'Years'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feature_type = models.CharField(max_length=50, choices=FEATURE_TYPE_CHOICES, unique=True)
    
    # Pricing options in both currencies
    price_htg = models.DecimalField(max_digits=12, decimal_places=2)
    price_usd = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Duration
    duration = models.IntegerField(validators=[MinValueValidator(1)])
    duration_unit = models.CharField(max_length=20, choices=DURATION_UNIT_CHOICES)
    
    # Details
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent"."premium_features'

    def __str__(self):
        return f"{self.get_feature_type_display()}"


class UserPremiumFeature(models.Model):
    """
    Tracks premium features purchased by users.
    Records purchase, activation, and expiration.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='premium_features')
    feature = models.ForeignKey(PremiumFeature, on_delete=models.PROTECT)
    
    # Related to specific event if applicable
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='premium_features'
    )
    
    # Payment and activation
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='HTG')
    
    activated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # Transaction reference
    transaction_id = models.CharField(max_length=255, unique=True, null=True, blank=True)

    class Meta:
        db_table = 'arkevent"."user_premium_features'
        indexes = [
            models.Index(fields=['user', 'expires_at']),
            models.Index(fields=['event', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user} - {self.feature}"
