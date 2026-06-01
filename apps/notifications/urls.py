from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationLogViewSet,
    EventNotificationSettingViewSet,
    PushTokenViewSet, UserDeviceViewSet
)

router = DefaultRouter()
router.register(r'notification-settings', EventNotificationSettingViewSet)
router.register(r'push-tokens', PushTokenViewSet)
router.register(r'devices', UserDeviceViewSet)
router.register(r'', NotificationLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]