import paypalrestsdk
from django.conf import settings
from .base import BasePaymentProvider

class PayPalProvider(BasePaymentProvider):
    def __init__(self):
        paypalrestsdk.configure({
            "mode": getattr(settings, 'PAYPAL_MODE', 'sandbox'),
            "client_id": getattr(settings, 'PAYPAL_CLIENT_ID', None),
            "client_secret": getattr(settings, 'PAYPAL_CLIENT_SECRET', None)
        })

    def create_payment_session(self, order):
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": f"{settings.SUPABASE_PUBLIC_URL}/payment/success?order_id={order.id}",
                "cancel_url": f"{settings.SUPABASE_PUBLIC_URL}/payment/cancel?order_id={order.id}"
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": f"Tickets for {order.event.title}",
                        "sku": str(order.id),
                        "price": str(order.total_amount),
                        "currency": order.currency,
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": str(order.total_amount),
                    "currency": order.currency
                },
                "description": f"Payment for Order {order.id}"
            }]
        })

        if payment.create():
            for link in payment.links:
                if link.rel == "approval_url":
                    return link.href
        return None

    def verify_webhook(self, request):
        auth_algo = request.META.get('HTTP_PAYPAL_AUTH_ALGO')
        cert_url = request.META.get('HTTP_PAYPAL_CERT_URL')
        transmission_id = request.META.get('HTTP_PAYPAL_TRANSMISSION_ID')
        transmission_sig = request.META.get('HTTP_PAYPAL_TRANSMISSION_SIG')
        transmission_time = request.META.get('HTTP_PAYPAL_TRANSMISSION_TIME')
        webhook_id = getattr(settings, 'PAYPAL_WEBHOOK_ID', None)

        event_body = request.body.decode('utf-8')

        is_valid = paypalrestsdk.WebhookEvent.verify(
            transmission_id, transmission_sig, transmission_time,
            webhook_id, event_body, cert_url, auth_algo
        )

        if is_valid:
            import json
            return json.loads(event_body)
        return None

    def handle_webhook(self, payload):
        if payload['event_type'] == 'PAYMENT.SALE.COMPLETED':
            sale = payload['resource']
            # We need to find the order_id. PayPal stores it in custom field or we can use SKU from items
            # For simplicity, assuming it's available or passed in parent_payment
            return {
                'order_id': sale.get('custom') or sale.get('invoice_number'),
                'transaction_id': sale['id'],
                'status': 'succeeded',
                'raw_data': sale
            }
        return None
