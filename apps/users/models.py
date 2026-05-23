from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, editable=False, unique=True)
    email = models.EmailField(unique=True, blank=False)
    username = models.CharField(max_length=150, blank=True, null=True, unique=True)

    # Champs supplémentaires de arkevent.profiles
    first_name = models.CharField(max_length=150, blank=True, default='')
    last_name = models.CharField(max_length=150, blank=True, default='')
    full_name = models.CharField(max_length=300, blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    phone_verified = models.BooleanField(default=False)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True, default='')
    location = models.CharField(max_length=255, blank=True, default='')
    user_timezone = models.CharField(max_length=50, blank=True, default='UTC')
    language = models.CharField(max_length=10, blank=True, default='fr')
    avatar_url = models.URLField(blank=True, default='')
    cover_url = models.URLField(blank=True, default='')
    bio = models.TextField(blank=True, default='')
    website = models.URLField(blank=True, default='')
    social_links = models.JSONField(default=dict, blank=True)
    role = models.CharField(max_length=20, default='user')  # 'user', 'controller', 'admin', 'superadmin'
    is_verified = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    notification_preferences = models.JSONField(default=dict, blank=True)
    settings = models.JSONField(default=dict, blank=True)
    referral_code = models.CharField(max_length=50, blank=True, default='')
    referred_by = models.UUIDField(null=True, blank=True)
    affiliate_id = models.UUIDField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    accepted_terms_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Remplace les champs de AbstractUser qui ne sont pas nécessaires
    # On garde password, last_login, is_active, is_staff, is_superuser, date_joined

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone', 'role']

    class Meta:
        db_table = 'arkevent.users'
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def __str__(self):
        return self.email

    def get_full_name(self):
        return self.full_name or f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name or self.email.split('@')[0]

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
                condition=models.Q(balance__gte=0),
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
    
class EmailVerificationToken(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    token = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.email_verification_tokens'

class PasswordResetToken(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    token = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.password_reset_tokens'

