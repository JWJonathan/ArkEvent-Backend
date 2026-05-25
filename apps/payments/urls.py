from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderItemViewSet, OrderViewSet, WebhookView, PaymentViewSet

router = DefaultRouter()
router.register(r'my-orders', OrderViewSet, basename='my-orders')
router.register(r'webhooks', WebhookView, basename='webhooks')
router.register(r'my-order-items', OrderItemViewSet, basename='my-order-items')
router.register(r'', PaymentViewSet, basename='payments')

urlpatterns = [
    path('mine/total-spent/', PaymentViewSet.as_view({'get': 'total_spent'}), name='total-spent'),
    path('', include(router.urls)),
]
