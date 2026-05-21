import json
import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .services import PaymentService
from .models import Order
from .serializers import OrderSerializer
import paypalrestsdk

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user_id=self.request.user.id)

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user.id)

class StripeWebhookView(APIView):
    permission_classes = [AllowAny]

    @csrf_exempt
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        event = None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            return HttpResponse(status=400)

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            order_id = session.get('client_reference_id') or session.get('metadata', {}).get('order_id')
            if order_id:
                PaymentService.process_successful_payment(
                    order_id=order_id,
                    gateway='stripe',
                    transaction_id=session.get('payment_intent'),
                    provider_response=event,
                    metadata=session.get('metadata')
                )

        return HttpResponse(status=200)

class PayPalWebhookView(APIView):
    permission_classes = [AllowAny]

    @csrf_exempt
    def post(self, request):
        paypalrestsdk.configure({
            "mode": "live" if not settings.DEBUG else "sandbox",
            "client_id": settings.PAYPAL_CLIENT_ID,
            "client_secret": settings.PAYPAL_CLIENT_SECRET
        })

        headers = request.META
        body = request.body.decode('utf-8')

        is_valid = paypalrestsdk.WebhookEvent.verify(
            headers.get('HTTP_PAYPAL_TRANSMISSION_ID'),
            headers.get('HTTP_PAYPAL_TRANSMISSION_TIME'),
            settings.PAYPAL_WEBHOOK_ID,
            body,
            headers.get('HTTP_PAYPAL_CERT_URL'),
            headers.get('HTTP_PAYPAL_TRANSMISSION_SIG'),
            headers.get('HTTP_PAYPAL_AUTH_ALGO')
        )

        if not is_valid:
            return HttpResponse("Invalid signature", status=400)

        data = json.loads(body)
        event_type = data.get('event_type')

        if event_type == 'PAYMENT.CAPTURE.COMPLETED':
            resource = data.get('resource')
            order_id = resource.get('custom_id')

            if order_id:
                PaymentService.process_successful_payment(
                    order_id=order_id,
                    gateway='paypal',
                    transaction_id=resource.get('id'),
                    provider_response=data,
                    metadata=resource.get('amount')
                )

        return HttpResponse(status=200)
