from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Order
from .serializers import OrderSerializer
from .providers.stripe import StripeProvider
from .providers.moncash import MonCashProvider
from .providers.paypal import PayPalProvider

class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user_id=self.request.user.id)

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        order = self.get_object()
        provider_name = request.data.get('provider')

        if order.status != 'pending':
            return Response({'error': 'Order is not in pending status'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if provider_name == 'stripe':
                provider = StripeProvider()
            elif provider_name == 'moncash':
                provider = MonCashProvider()
            elif provider_name == 'paypal':
                provider = PayPalProvider()
            else:
                return Response({'error': 'Unsupported payment provider'}, status=status.HTTP_400_BAD_REQUEST)

            payment_url = provider.create_payment_session(order)
            return Response({'payment_url': payment_url})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class WebhookView(viewsets.GenericViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['post'], url_path='stripe')
    def stripe_webhook(self, request):
        provider = StripeProvider()
        event = provider.verify_webhook(request)
        if event:
            data = provider.handle_webhook(event)
            if data:
                from .services import PaymentService
                PaymentService.process_successful_payment(
                    order_id=data['order_id'],
                    provider_name='stripe',
                    transaction_id=data['transaction_id'],
                    raw_data=data['raw_data']
                )
                return Response({'status': 'success'})
        return Response({'status': 'invalid payload'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='paypal')
    def paypal_webhook(self, request):
        provider = PayPalProvider()
        event = provider.verify_webhook(request)
        if event:
            data = provider.handle_webhook(event)
            if data:
                from .services import PaymentService
                PaymentService.process_successful_payment(
                    order_id=data['order_id'],
                    provider_name='paypal',
                    transaction_id=data['transaction_id'],
                    raw_data=data['raw_data']
                )
                return Response({'status': 'success'})
        return Response({'status': 'invalid payload'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='moncash')
    def moncash_webhook(self, request):
        provider = MonCashProvider()
        event = provider.verify_webhook(request)
        if event:
            data = provider.handle_webhook(event)
            if data:
                from .services import PaymentService
                PaymentService.process_successful_payment(
                    order_id=data['order_id'],
                    provider_name='moncash',
                    transaction_id=data['transaction_id'],
                    raw_data=data['raw_data']
                )
                return Response({'status': 'success'})
        return Response({'status': 'invalid payload'}, status=status.HTTP_400_BAD_REQUEST)
