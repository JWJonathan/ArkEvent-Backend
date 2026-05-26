from django.contrib import admin
from .models import (
    Coupon, CouponUsage, GiftCard, GiftCardTransaction,
    LoyaltyPoint, LoyaltyTransaction, Affiliate, AffiliateTransaction,
    Wishlist, Review, ReviewLike, UserTag
)

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'organization', 'event', 'discount_type', 'discount_value', 'is_active')
    list_filter = ('discount_type', 'is_active', 'created_at')
    search_fields = ('code', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('organization', 'event', 'created_by')

@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ('coupon', 'user', 'order', 'discount_applied', 'used_at')
    list_filter = ('used_at',)
    search_fields = ('coupon__code', 'user__email')
    readonly_fields = ('id', 'used_at')
    raw_id_fields = ('coupon', 'user', 'order')

@admin.register(GiftCard)
class GiftCardAdmin(admin.ModelAdmin):
    list_display = ('code', 'initial_amount', 'balance', 'currency', 'purchaser', 'is_redeemed')
    list_filter = ('currency', 'is_redeemed', 'created_at')
    search_fields = ('code', 'purchaser__email', 'recipient_email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('purchaser',)

@admin.register(GiftCardTransaction)
class GiftCardTransactionAdmin(admin.ModelAdmin):
    list_display = ('gift_card', 'order', 'amount', 'transaction_type', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('gift_card__code',)
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('gift_card', 'order')

@admin.register(LoyaltyPoint)
class LoyaltyPointAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'updated_at')
    search_fields = ('user__email',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('user',)

@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'points', 'type', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('user__email', 'description')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('user', 'order')

@admin.register(Affiliate)
class AffiliateAdmin(admin.ModelAdmin):
    list_display = ('code', 'user', 'organization', 'commission_rate', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('code', 'user__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('user', 'organization')

@admin.register(AffiliateTransaction)
class AffiliateTransactionAdmin(admin.ModelAdmin):
    list_display = ('affiliate', 'order', 'commission_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('affiliate__code', 'order__id')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('affiliate', 'order')

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'created_at')
    search_fields = ('user__email', 'event__title')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('user', 'event')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'rating', 'is_verified_purchase', 'is_visible', 'created_at')
    list_filter = ('rating', 'is_verified_purchase', 'is_visible', 'created_at')
    search_fields = ('event__title', 'user__email', 'title', 'comment')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('event', 'user')

@admin.register(ReviewLike)
class ReviewLikeAdmin(admin.ModelAdmin):
    list_display = ('review', 'user', 'created_at')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('review', 'user')

@admin.register(UserTag)
class UserTagAdmin(admin.ModelAdmin):
    list_display = ('user', 'tag', 'created_at')
    list_filter = ('tag', 'created_at')
    search_fields = ('user__email', 'tag')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('user',)
