from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmailCampaignViewSet, EmailSubscriberViewSet

router = DefaultRouter()
router.register(r'campaigns', EmailCampaignViewSet)
router.register(r'subscribers', EmailSubscriberViewSet)

urlpatterns = [
    path('', include(router.urls)),
]