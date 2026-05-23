from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
import uuid


class Coupon(models.Model):
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed_amount', 'Fixed Amount'),
    ]
    id = models.UUIDField(primary_key=True, editable=False)
    organization = models.ForeignKey('organization.Organization', null=True, blank=True, on_delete=models.CASCADE, db_column='organization_id', related_name='coupons')
    event = models.ForeignKey('events.Event', null=True, blank=True, on_delete=models.CASCADE, db_column='event_id', related_name='coupons')
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, default='')
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    max_uses_per_user = models.PositiveIntegerField(default=1)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    applicable_ticket_types = models.JSONField(default=list, blank=True)  # liste d'UUID de ticket types
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'arkevent.coupons'

    def __str__(self):
        return self.code


class CouponUsage(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, db_column='coupon_id', related_name='usages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='user_id')
    order = models.ForeignKey('payments.Order', null=True, blank=True, on_delete=models.SET_NULL, db_column='order_id')
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.coupon_usages'
        unique_together = ('coupon', 'user', 'order')

    def __str__(self):
        return f"{self.coupon.code} used by {self.user.email}"

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

class GiftCard(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    code = models.CharField(max_length=50, unique=True)
    initial_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    balance = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default='HTG')
    purchaser = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, db_column='purchaser_id', related_name='purchased_gift_cards')
    recipient_email = models.EmailField(blank=True, default='')
    message = models.TextField(blank=True, default='')
    is_redeemed = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent.gift_cards'

    def __str__(self):
        return self.code

class GiftCardTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('redemption', 'Redemption'),
        ('refund', 'Refund'),
    ]
    id = models.UUIDField(primary_key=True, editable=False)
    gift_card = models.ForeignKey(GiftCard, on_delete=models.CASCADE, db_column='gift_card_id', related_name='transactions')
    order = models.ForeignKey('payments.Order', null=True, blank=True, on_delete=models.SET_NULL, db_column='order_id')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.gift_card_transactions'

    def __str__(self):
        return f"{self.transaction_type} {self.amount}"


class LoyaltyPoint(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='user_id', related_name='loyalty_points')
    balance = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent.loyalty_points'

    def __str__(self):
        return f"{self.user.email} - {self.balance} pts"


class LoyaltyTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('earn', 'Earn'),
        ('redeem', 'Redeem'),
        ('expire', 'Expire'),
        ('adjustment', 'Adjustment'),
    ]
    id = models.UUIDField(primary_key=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='user_id', related_name='loyalty_transactions')
    order = models.ForeignKey('payments.Order', null=True, blank=True, on_delete=models.SET_NULL, db_column='order_id')
    points = models.IntegerField()
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    description = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.loyalty_transactions'

    def __str__(self):
        return f"{self.type} {self.points} pts"


class Affiliate(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, db_column='user_id', related_name='affiliations')
    organization = models.ForeignKey('organization.Organization', null=True, blank=True, on_delete=models.CASCADE, db_column='organization_id', related_name='affiliates')
    code = models.CharField(max_length=50, unique=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent.affiliates'

    def __str__(self):
        return self.code


class AffiliateTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    id = models.UUIDField(primary_key=True, editable=False)
    affiliate = models.ForeignKey(Affiliate, on_delete=models.CASCADE, db_column='affiliate_id', related_name='transactions')
    order = models.ForeignKey('payments.Order', on_delete=models.CASCADE, db_column='order_id')
    order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.affiliate_transactions'

    def __str__(self):
        return f"Com. {self.commission_amount} for order {self.order_id}"
    

from django.core.validators import MinValueValidator, MaxValueValidator

class Wishlist(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='user_id', related_name='wishlists')
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, db_column='event_id', related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.wishlists'
        unique_together = ('user', 'event')

    def __str__(self):
        return f"{self.user.email} -> {self.event.title}"


class Review(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, db_column='event_id', related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='user_id', related_name='reviews')
    rating = models.DecimalField(max_digits=2, decimal_places=1, validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=255, blank=True, default='')
    comment = models.TextField(blank=True, default='')
    is_verified_purchase = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)
    likes_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'arkevent.reviews'
        unique_together = ('event', 'user')

    def __str__(self):
        return f"Review by {self.user.email} for {self.event.title}"


class ReviewLike(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    review = models.ForeignKey(Review, on_delete=models.CASCADE, db_column='review_id', related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='user_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.review_likes'
        unique_together = ('review', 'user')

    def __str__(self):
        return f"Like by {self.user.email} on review {self.review.id}"


class UserTag(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='user_id', related_name='tags')
    tag = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.user_tags'
        unique_together = ('user', 'tag')

    def __str__(self):
        return f"{self.tag} ({self.user.email})"
    