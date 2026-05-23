from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.core.views import CouponViewSet, CouponUsageViewSet
from .views import (
    GiftCardViewSet, GiftCardTransactionViewSet,
    LoyaltyPointViewSet, LoyaltyTransactionViewSet,
    AffiliateViewSet, AffiliateTransactionViewSet,
    WishlistViewSet, ReviewViewSet, UserTagViewSet
)

router = DefaultRouter()
router.register(r'coupons', CouponViewSet)
router.register(r'coupon-usages', CouponUsageViewSet)
router.register(r'gift-cards', GiftCardViewSet)
router.register(r'gift-card-transactions', GiftCardTransactionViewSet)
router.register(r'loyalty-points', LoyaltyPointViewSet)
router.register(r'loyalty-transactions', LoyaltyTransactionViewSet)
router.register(r'affiliates', AffiliateViewSet)
router.register(r'affiliate-transactions', AffiliateTransactionViewSet)
router.register(r'wishlist', WishlistViewSet, basename='wishlist')
router.register(r'reviews', ReviewViewSet)
router.register(r'tags', UserTagViewSet)

urlpatterns = [
    path('', include(router.urls)),
]