
from rest_framework import serializers
from apps.core.models import Coupon, CouponUsage


class CouponSerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')
    organization_name = serializers.ReadOnlyField(source='organization.name')

    class Meta:
        model = Coupon
        fields = [
            'id', 'organization_id', 'organization_name', 'event_id', 'event_title',
            'code', 'description', 'discount_type', 'discount_value',
            'min_order_amount', 'max_uses', 'max_uses_per_user',
            'valid_from', 'valid_to', 'applicable_ticket_types',
            'is_active', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CouponUsageSerializer(serializers.ModelSerializer):
    coupon_code = serializers.ReadOnlyField(source='coupon.code')
    user_email = serializers.ReadOnlyField(source='user.email')

    class Meta:
        model = CouponUsage
        fields = ['id', 'coupon_id', 'coupon_code', 'user_id', 'user_email', 'order_id', 'discount_applied', 'used_at']
        read_only_fields = ['id', 'used_at']



from rest_framework import serializers
from .models import GiftCard, GiftCardTransaction, LoyaltyPoint, LoyaltyTransaction, Affiliate, AffiliateTransaction

class GiftCardSerializer(serializers.ModelSerializer):
    purchaser_name = serializers.ReadOnlyField(source='purchaser.profile.full_name')

    class Meta:
        model = GiftCard
        fields = [
            'id', 'code', 'initial_amount', 'balance', 'currency',
            'purchaser_id', 'purchaser_name', 'recipient_email', 'message',
            'is_redeemed', 'expires_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class GiftCardTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftCardTransaction
        fields = ['id', 'gift_card_id', 'order_id', 'amount', 'transaction_type', 'created_at']
        read_only_fields = ['id', 'created_at']

class LoyaltyPointSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.profile.full_name')

    class Meta:
        model = LoyaltyPoint
        fields = ['id', 'user_id', 'user_name', 'balance', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class LoyaltyTransactionSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.profile.full_name')

    class Meta:
        model = LoyaltyTransaction
        fields = ['id', 'user_id', 'user_name', 'order_id', 'points', 'type', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']

class AffiliateSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.profile.full_name')
    organization_name = serializers.ReadOnlyField(source='organization.name')

    class Meta:
        model = Affiliate
        fields = [
            'id', 'user_id', 'user_name', 'organization_id', 'organization_name',
            'code', 'commission_rate', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class AffiliateTransactionSerializer(serializers.ModelSerializer):
    affiliate_code = serializers.ReadOnlyField(source='affiliate.code')

    class Meta:
        model = AffiliateTransaction
        fields = ['id', 'affiliate_id', 'affiliate_code', 'order_id', 'order_amount', 'commission_amount', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']


from rest_framework import serializers
from .models import Wishlist, Review, ReviewLike, UserTag
#from .serializers import EventSerializer  # pour l'imbrication éventuelle

class WishlistSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.profile.full_name')
    event_title = serializers.ReadOnlyField(source='event.title')

    class Meta:
        model = Wishlist
        fields = ['id', 'user_id', 'user_name', 'event_id', 'event_title', 'created_at']
        read_only_fields = ['id', 'created_at']

class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.profile.full_name')
    event_title = serializers.ReadOnlyField(source='event.title')

    class Meta:
        model = Review
        fields = [
            'id', 'event_id', 'event_title', 'user_id', 'user_name',
            'rating', 'title', 'comment', 'is_verified_purchase',
            'is_visible', 'likes_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'likes_count', 'created_at', 'updated_at']

class ReviewLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewLike
        fields = ['id', 'review_id', 'user_id', 'created_at']
        read_only_fields = ['id', 'created_at']

class UserTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserTag
        fields = ['id', 'user_id', 'tag', 'created_at']
        read_only_fields = ['id', 'created_at']
