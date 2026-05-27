from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    SubscriptionPlanViewSet, UserSubscriptionViewSet,
    PremiumFeatureViewSet, UserPremiumFeatureViewSet
)

router = DefaultRouter()
router.register(r'plans', SubscriptionPlanViewSet, basename='plans')
router.register(r'premium-features', PremiumFeatureViewSet, basename='premium-features')
router.register(r'user-premium-features', UserPremiumFeatureViewSet, basename='user-premium-features')
router.register(r'sub', UserSubscriptionViewSet, basename='user-subscriptions')

urlpatterns = [
    path('', include(router.urls)),
]
