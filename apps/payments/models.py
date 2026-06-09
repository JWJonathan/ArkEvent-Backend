from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from apps.events.models import Event


# ============================================================================
# COMMISSION & REVENUE MODELS
# ============================================================================

class CommissionRule(models.Model):
    """
    Flexible commission rules for different subscription tiers and contexts.
    Supports percentage, fixed, and hybrid commission types.
    """
    COMMISSION_TYPE_CHOICES = [
        ('percentage', 'Percentage Based (%)'),
        ('fixed', 'Fixed Amount'),
        ('hybrid', 'Percentage + Fixed'),
    ]
    
    DEDUCTION_MODEL_CHOICES = [
        ('organizer', 'Deducted from Organizer Revenue'),
        ('customer', 'Added to Customer Checkout'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    commission_type = models.CharField(max_length=20, choices=COMMISSION_TYPE_CHOICES)
    deduction_model = models.CharField(
        max_length=20, 
        choices=DEDUCTION_MODEL_CHOICES,
        default='organizer'
    )
    
    # For percentage type
    percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # For fixed and hybrid types
    fixed_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)]
    )
    fixed_currency = models.CharField(
        max_length=3, 
        default='USD',
        help_text='Currency for fixed amount'
    )
    
    # Applies to which subscription tier (NULL = all)
    subscription_tier = models.CharField(
        max_length=20,
        choices=[
            ('free', 'Free Plan'),
            ('pro', 'Pro Plan'),
            ('business', 'Business Plan'),
        ],
        null=True,
        blank=True
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent"."commission_rules'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.get_commission_type_display()}"


class TicketSale(models.Model):
    """
    Record of individual ticket sale transaction with commission details.
    """
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partial_refund', 'Partial Refund'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name='ticket_sales')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ticket_purchases')
    
    # Basic transaction info
    ticket_quantity = models.IntegerField(validators=[MinValueValidator(1)])
    ticket_price_per_unit = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    # Revenue breakdown
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)  # ticket_quantity * ticket_price_per_unit
    platform_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Platform fee if added to checkout
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)  # Deducted from organizer
    organizer_net_revenue = models.DecimalField(max_digits=12, decimal_places=2)  # subtotal - commission
    total_amount_paid = models.DecimalField(max_digits=12, decimal_places=2)  # subtotal + platform_fee
    
    # Commission info
    commission_rule = models.ForeignKey(CommissionRule, on_delete=models.SET_NULL, null=True)
    
    # Status and tracking
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent"."ticket_sales'
        indexes = [
            models.Index(fields=['event', 'created_at']),
            models.Index(fields=['buyer', 'created_at']),
            models.Index(fields=['payment_status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Sale #{self.id} - {self.ticket_quantity} tickets"


class Invoice(models.Model):
    """
    Invoice generated for ticket sales, visible to both buyer and organizer.
    """
    INVOICE_TYPE_CHOICES = [
        ('sale', 'Ticket Sale'),
        ('refund', 'Refund'),
        ('subscription', 'Subscription'),
        ('premium_feature', 'Premium Feature'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_type = models.CharField(max_length=20, choices=INVOICE_TYPE_CHOICES)
    
    # Related transactions
    ticket_sale = models.OneToOneField(TicketSale, on_delete=models.CASCADE, null=True, blank=True, related_name='invoice')
    
    # Parties involved
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='invoices_as_buyer')
    seller = models.ForeignKey(
        'organization.Organization',
        on_delete=models.PROTECT,
        related_name='invoices_as_seller',
        null=True,
        blank=True
    )
    
    # Amount info
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    # Status
    issued_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Additional info
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent"."invoices'
        ordering = ['-issued_at']

    def __str__(self):
        return f"Invoice {self.invoice_number}"


class PaymentMethod(models.Model):
    """
    User's saved payment methods for quick checkout.
    Supports multiple providers: MonCash, NatCash, Digicel, cards.
    """
    METHOD_TYPE_CHOICES = [
        ('moncash', 'MonCash'),
        ('natcash', 'NatCash'),
        ('digicel', 'Digicel Payment'),
        ('card', 'Credit/Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payment_methods')
    
    method_type = models.CharField(max_length=20, choices=METHOD_TYPE_CHOICES)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Encrypted or tokenized payment info (don't store raw details)
    token = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(max_length=100)  # e.g., "Digicel ending in 4242"
    
    # Provider-specific metadata
    provider_metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent"."payment_methods'

    def __str__(self):
        return f"{self.get_method_type_display()} - {self.display_name}"


class RefundRequest(models.Model):
    """
    Track refund requests and their status.
    """
    REFUND_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
    ]
    
    REFUND_REASON_CHOICES = [
        ('duplicate', 'Duplicate Charge'),
        ('not_as_described', 'Not As Described'),
        ('cant_attend', "Can't Attend"),
        ('event_cancelled', 'Event Cancelled'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_sale = models.OneToOneField(TicketSale, on_delete=models.PROTECT, related_name='refund_request')
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    refund_reason = models.CharField(max_length=50, choices=REFUND_REASON_CHOICES)
    reason_description = models.TextField()
    
    status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='refunds_reviewed'
    )
    review_notes = models.TextField(blank=True)
    
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'arkevent"."refund_requests'
        ordering = ['-requested_at']

    def __str__(self):
        return f"Refund {self.id} - {self.status}"


# ============================================================================
# LEGACY ORDER MODELS (kept for backward compatibility)
# ============================================================================

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('awaiting_payment', 'Awaiting Payment'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders", db_column='user_id')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="orders", db_column='event_id')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.TextField(default="USD")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'arkevent"."orders'

class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", db_column='order_id')
    ticket_type = models.ForeignKey("tickets.TicketType", on_delete=models.CASCADE, db_column='ticket_type_id')
    quantity = models.IntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent"."order_items'

class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments", db_column='order_id')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments", db_column='user_id')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.TextField(default="USD")
    transaction_id = models.TextField(unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, default="initiated")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent"."payments'
