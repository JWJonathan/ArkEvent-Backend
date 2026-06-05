from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    CommissionRuleViewSet, TicketSaleViewSet, InvoiceViewSet,
    PaymentMethodViewSet, RefundRequestViewSet, OrderViewSet, PaymentViewSet,
    OrderItemViewSet, WebhookView
)

router = DefaultRouter()

# New financial API endpoints
router.register(r'commission-rules', CommissionRuleViewSet, basename='commission-rules')
router.register(r'ticket-sales', TicketSaleViewSet, basename='ticket-sales')
router.register(r'invoices', InvoiceViewSet, basename='invoices')
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-methods')
router.register(r'refund-requests', RefundRequestViewSet, basename='refund-requests')
router.register(r'order-items', OrderItemViewSet, basename='order-items')
router.register(r'webhooks', WebhookView, basename='webhooks')

# Legacy endpoints (maintain backward compatibility)
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'', PaymentViewSet, basename='payments')

urlpatterns = [
    path('', include(router.urls)),
]

