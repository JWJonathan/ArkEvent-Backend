from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StripeWebhookView, PayPalWebhookView, OrderViewSet

router = DefaultRouter()
router.register(r'orders', OrderViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('webhooks/stripe/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('webhooks/paypal/', PayPalWebhookView.as_view(), name='paypal-webhook'),
]
