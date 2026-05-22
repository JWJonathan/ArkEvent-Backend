from django.db import models
import uuid

class Profile(models.Model):
    id = models.UUIDField(primary_key=True, editable=False) # References auth.users(id)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    phone = models.TextField(null=True, blank=True)
    phone_verified = models.BooleanField(default=False)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    timezone = models.TextField(default="UTC")
    language = models.TextField(default="fr")
    avatar_url = models.TextField(null=True, blank=True)
    cover_url = models.TextField(null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)
    social_links = models.JSONField(default=dict)
    role = models.CharField(max_length=20, default="user")
    is_verified = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    notification_preferences = models.JSONField(default=dict)
    settings = models.JSONField(default=dict)
    referral_code = models.TextField(unique=True, null=True, blank=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, db_column='referred_by')
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent"."profiles'

    def __str__(self):
        return self.username or str(self.id)


from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings

class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, unique=True)  # sera géré par la BDD
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet',
        db_column='user_id'
    )
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.00)]
    )
    currency = models.CharField(max_length=3, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent.wallets'
        constraints = [
            models.CheckConstraint(
                check=models.Q(balance__gte=0),
                name='wallet_balance_non_negative'
            )
        ]

    def __str__(self):
        return f"{self.user.email} – {self.balance} {self.currency}"


class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('credit', 'Credit'),
    ]
    TRANSACTION_STATUSES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet_transactions',
        db_column='user_id'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUSES, default='completed')
    description = models.CharField(max_length=255, blank=True)
    order = models.ForeignKey(
        'payments.Order',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column='order_id'
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.wallet_transactions'

    def __str__(self):
        return f"{self.type} – {self.amount} ({self.status})"
    
    