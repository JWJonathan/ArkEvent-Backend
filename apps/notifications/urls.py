from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationLogViewSet,
    EventNotificationSettingViewSet,
    PushTokenViewSet
)

router = DefaultRouter()
router.register(r'notifications', NotificationLogViewSet)
router.register(r'notification-settings', EventNotificationSettingViewSet)
router.register(r'push-tokens', PushTokenViewSet)

urlpatterns = [
    path('', include(router.urls)),
]