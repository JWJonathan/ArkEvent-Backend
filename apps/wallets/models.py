from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
import uuid


class Wallet(models.Model):
    """
    User wallet for storing funds and managing transactions.
    Tracks available balance, pending balance, and transaction history.
    """
    CURRENCY_CHOICES = [
        ('HTG', 'Haitian Gourde'),
        ('USD', 'US Dollar'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    
    # Balance tracking
    available_balance = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)]
    )
    pending_balance = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)]
    )
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='HTG')
    
    # Account status
    is_frozen = models.BooleanField(default=False, help_text="Freeze wallet during disputes or investigations")
    freeze_reason = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent"."wallets'
        indexes = [
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"Wallet: {self.user} - {self.available_balance} {self.currency}"

    @property
    def total_balance(self):
        """Total balance = available + pending"""
        return self.available_balance + self.pending_balance


class WalletTransaction(models.Model):
    """
    Individual transaction record in wallet.
    Immutable ledger entry for audit trail.
    """
    TRANSACTION_TYPE_CHOICES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('ticket_sale', 'Ticket Sale Commission'),
        ('refund', 'Refund'),
        ('payout', 'Payout'),
        ('subscription_charge', 'Subscription Charge'),
        ('premium_feature_charge', 'Premium Feature Charge'),
        ('adjustment', 'Manual Adjustment'),
    ]
    
    TRANSACTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='transactions')
    
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES, default='pending')
    
    # Amount info
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default='HTG')
    
    # Balance snapshot after transaction
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Reference and description
    reference_id = models.CharField(max_length=255, blank=True)  # TicketSale ID, Deposit ID, etc.
    description = models.TextField(blank=True)
    
    # Related objects
    related_ticket_sale = models.ForeignKey(
        'payments.TicketSale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wallet_transactions'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'arkevent"."wallet_transactions'
        indexes = [
            models.Index(fields=['wallet', 'created_at']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['status']),
            models.Index(fields=['reference_id']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount} {self.currency}"


class Deposit(models.Model):
    """
    User deposits money into their wallet.
    Tracks deposit source and payment details.
    """
    DEPOSIT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    DEPOSIT_METHOD_CHOICES = [
        ('moncash', 'MonCash'),
        ('natcash', 'NatCash'),
        ('digicel', 'Digicel Payment'),
        ('card', 'Credit/Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='deposits')
    
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, choices=[('HTG', 'HTG'), ('USD', 'USD')], default='HTG')
    
    deposit_method = models.CharField(max_length=20, choices=DEPOSIT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=DEPOSIT_STATUS_CHOICES, default='pending')
    
    # Transaction reference
    transaction_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    payment_method = models.ForeignKey(
        'payments.PaymentMethod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'arkevent"."deposits'
        indexes = [
            models.Index(fields=['wallet', 'created_at']),
            models.Index(fields=['status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Deposit {self.id} - {self.amount} {self.currency}"


class Withdrawal(models.Model):
    """
    User withdraws money from wallet.
    Tracks withdrawal destination and processing status.
    """
    WITHDRAWAL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('rejected', 'Rejected'),
    ]
    
    WITHDRAWAL_SPEED_CHOICES = [
        ('standard', 'Standard (Free)'),
        ('instant', 'Instant (100 HTG fee)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='withdrawals')
    
    # Amount info
    requested_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, choices=[('HTG', 'HTG'), ('USD', 'USD')], default='HTG')
    fee_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)  # requested_amount - fee_amount
    
    # Withdrawal details
    withdrawal_speed = models.CharField(max_length=20, choices=WITHDRAWAL_SPEED_CHOICES, default='standard')
    status = models.CharField(max_length=20, choices=WITHDRAWAL_STATUS_CHOICES, default='pending')
    
    # Destination (flexible to support multiple providers)
    destination_provider = models.CharField(max_length=50)  # moncash, natcash, digicel, bank, etc.
    destination_identifier = models.CharField(max_length=255)  # Phone number, account number, etc.
    
    # Transaction tracking
    transaction_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    
    # Processing info
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='withdrawals_processed'
    )
    rejection_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'arkevent"."withdrawals'
        indexes = [
            models.Index(fields=['wallet', 'created_at']),
            models.Index(fields=['status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Withdrawal {self.id} - {self.net_amount} {self.currency}"


class Payout(models.Model):
    """
    System-initiated payout to organizers.
    Different from user-initiated withdrawals - auto-triggered by system.
    """
    PAYOUT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('scheduled', 'Scheduled'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='payouts')
    
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default='HTG')
    
    status = models.CharField(max_length=20, choices=PAYOUT_STATUS_CHOICES, default='pending')
    
    # Payout period
    payout_period_start = models.DateField()
    payout_period_end = models.DateField()
    
    # Destination
    destination_provider = models.CharField(max_length=50)
    destination_identifier = models.CharField(max_length=255)
    
    # Transaction tracking
    transaction_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    
    # Summary of transactions included
    included_ticket_sales_count = models.IntegerField(default=0)
    included_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'arkevent"."payouts'
        indexes = [
            models.Index(fields=['wallet', 'created_at']),
            models.Index(fields=['status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Payout {self.id} - {self.amount} {self.currency}"
