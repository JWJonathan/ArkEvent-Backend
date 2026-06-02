from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    MarketplaceCategoryViewSet, MarketplaceProviderViewSet, 
    MarketplaceServiceViewSet, ServiceReviewViewSet,
    ServiceBookingViewSet, ServiceFavoriteViewSet,
    MarketplaceMessageViewSet
)

router = DefaultRouter()
router.register(r'categories', MarketplaceCategoryViewSet, basename='category')
router.register(r'providers', MarketplaceProviderViewSet, basename='provider')
router.register(r'services', MarketplaceServiceViewSet, basename='service')
router.register(r'reviews', ServiceReviewViewSet, basename='review')
router.register(r'bookings', ServiceBookingViewSet, basename='booking')
router.register(r'favorites', ServiceFavoriteViewSet, basename='favorite')
router.register(r'messages', MarketplaceMessageViewSet, basename='message')

urlpatterns = [
    path('', include(router.urls)),
]
