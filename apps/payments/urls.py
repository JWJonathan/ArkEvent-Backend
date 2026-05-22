from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderItemViewSet, OrderViewSet, WebhookView, PaymentViewSet

router = DefaultRouter()
router.register(r'my-orders', OrderViewSet, basename='my-orders')
router.register(r'webhooks', WebhookView, basename='webhooks')
router.register(r'payments', PaymentViewSet)
router.register(r'my-order-items', OrderItemViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
