from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, WebhookView

router = DefaultRouter()
router.register(r'my-orders', OrderViewSet, basename='my-orders')
router.register(r'webhooks', WebhookView, basename='webhooks')

urlpatterns = [
    path('', include(router.urls)),
]
