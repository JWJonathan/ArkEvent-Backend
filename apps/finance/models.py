from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
import uuid


class PlatformRevenue(models.Model):
    """
    Track platform revenue from commissions, subscriptions, and premium features.
    Daily and monthly aggregates for reporting.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Time period
    revenue_date = models.DateField()
    revenue_month = models.DateField(help_text="First day of month")
    
    # Revenue breakdown
    ticket_commission_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subscription_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    premium_feature_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    event_boost_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    
    # Transaction counts
    ticket_sales_count = models.IntegerField(default=0)
    new_subscriptions_count = models.IntegerField(default=0)
    premium_features_purchased_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent.platform_revenue'
        indexes = [
            models.Index(fields=['revenue_date']),
            models.Index(fields=['revenue_month']),
        ]
        unique_together = [['revenue_date', 'currency']]
        ordering = ['-revenue_date']

    def __str__(self):
        return f"Revenue {self.revenue_date} - {self.total_revenue} {self.currency}"


class RevenueReport(models.Model):
    """
    Detailed revenue report for organizers.
    Aggregates sales, commissions, and earnings for a period.
    """
    REPORT_PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizer = models.ForeignKey(
        'organization.Organization',
        on_delete=models.CASCADE,
        related_name='revenue_reports'
    )
    
    period_type = models.CharField(max_length=20, choices=REPORT_PERIOD_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Revenue metrics
    gross_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    total_commissions = models.DecimalField(max_digits=12, decimal_places=2)
    net_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    # Transaction details
    total_ticket_sales = models.IntegerField()
    total_tickets_sold = models.IntegerField()
    average_ticket_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Events
    events_count = models.IntegerField()
    top_event = models.ForeignKey(
        'events.Event',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    
    # Refunds
    refunds_count = models.IntegerField(default=0)
    refunds_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.revenue_reports'
        indexes = [
            models.Index(fields=['organizer', 'start_date']),
            models.Index(fields=['period_type', 'start_date']),
        ]
        ordering = ['-start_date']

    def __str__(self):
        return f"Revenue Report - {self.organizer} ({self.start_date} to {self.end_date})"


class EventBoost(models.Model):
    """
    Premium feature: boost event visibility.
    Tracks when event is boosted and its visibility metrics.
    """
    BOOST_TYPE_CHOICES = [
        ('homepage', 'Homepage Featured'),
        ('trending', 'Trending Section'),
        ('search_priority', 'Search Priority'),
        ('recommendation', 'Recommendation Boost'),
    ]
    
    BOOST_DURATION_CHOICES = [
        ('7days', '7 Days - 20 USD'),
        ('30days', '30 Days - 50 USD'),
        ('90days', '90 Days - 100 USD'),
        ('180days', '180 Days - 200 USD'),
        ('365days', '365 Days - 500 USD'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='boosts')
    
    boost_type = models.CharField(max_length=30, choices=BOOST_TYPE_CHOICES)
    duration = models.CharField(max_length=20, choices=BOOST_DURATION_CHOICES)
    
    # Financial tracking
    cost_htg = models.DecimalField(max_digits=12, decimal_places=2)
    cost_usd = models.DecimalField(max_digits=12, decimal_places=2)
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    
    # Dates
    activated_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # Metrics
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    conversions = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.event_boosts'
        indexes = [
            models.Index(fields=['event', 'is_active']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Boost - {self.event} ({self.get_boost_type_display()})"


class AnalyticsDailyMetric(models.Model):
    """
    Daily analytics snapshot for events and platform.
    Used for reporting and trend analysis.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='daily_metrics')
    
    metric_date = models.DateField()
    
    # Views and interactions
    page_views = models.IntegerField(default=0)
    unique_visitors = models.IntegerField(default=0)
    
    # Ticket sales
    tickets_sold = models.IntegerField(default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    
    # Refunds
    refunds = models.IntegerField(default=0)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.analytics_daily_metrics'
        indexes = [
            models.Index(fields=['event', 'metric_date']),
        ]
        unique_together = [['event', 'metric_date']]

    def __str__(self):
        return f"{self.event} - {self.metric_date}"
