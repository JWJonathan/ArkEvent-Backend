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

    def create_payment_session(self, obj, user=None, return_url=None, cancel_url=None):
        """
        Creates a PayPal payment session for an Order, SubscriptionPlan, ServiceBooking, or Deposit.
        'user' is the user object performing the purchase.
        """
        from apps.payments.models import Order
        from apps.subscriptions.models import SubscriptionPlan
        from apps.marketplace.models import ServiceBooking
        from apps.wallets.models import Deposit
        
        user_id_str = str(user.id) if user else ""
        
        if isinstance(obj, Order):
            item_name = f"Tickets for {obj.event.title}"
            item_sku = f"ORDER_{obj.id}"
            custom_field = f"ORDER:{obj.id}:{user_id_str}"
            amount = str(obj.total_amount)
            currency = obj.currency
            description = f"Payment for Order {obj.id}"
            default_return = f"arkevent://payment/success?order_id={obj.id}"
            default_cancel = f"arkevent://payment/cancel?order_id={obj.id}"
        elif isinstance(obj, SubscriptionPlan):
            item_name = f"Subscription: {obj.name} ({obj.tier})"
            item_sku = f"SUB_{obj.tier}"
            custom_field = f"SUB:{obj.tier}:{user_id_str}"
            amount = str(obj.price_usd)
            currency = "USD"
            description = f"Subscription Plan: {obj.name}"
            default_return = f"arkevent://subscription/success?tier={obj.tier}"
            default_cancel = "arkevent://subscription/cancel"
        elif isinstance(obj, ServiceBooking):
            item_name = f"Booking: {obj.service.title}"
            item_sku = f"BOOKING_{obj.reference}"
            custom_field = f"BOOKING:{obj.id}:{user_id_str}"
            amount = str(obj.total_amount)
            currency = obj.service.currency or "USD"
            description = f"Service Booking: {obj.reference}"
            default_return = f"arkevent://marketplace/booking/success?ref={obj.reference}"
            default_cancel = "arkevent://marketplace/booking/cancel"
        elif isinstance(obj, Deposit):
            item_name = f"Wallet Deposit"
            item_sku = f"DEPOSIT_{obj.id}"
            custom_field = f"DEPOSIT:{obj.id}:{user_id_str}"
            amount = str(obj.amount)
            currency = obj.currency
            description = f"Wallet Deposit: {obj.id}"
            default_return = "arkevent://wallet/deposit/success"
            default_cancel = "arkevent://wallet/deposit/cancel"
        else:
            raise ValueError("Unsupported object type for PayPal payment")

        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": return_url or default_return,
                "cancel_url": cancel_url or default_cancel
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": item_name,
                        "sku": item_sku,
                        "price": amount,
                        "currency": currency,
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": amount,
                    "currency": currency
                },
                "description": description,
                "custom": custom_field
            }]
        })

        if payment.create():
            for link in payment.links:
                if link.rel == "approval_url":
                    return {
                        'approval_url': link.href,
                        'payment_id': payment.id
                    }
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
