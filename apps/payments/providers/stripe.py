import stripe
from django.conf import settings
from .base import BasePaymentProvider

class StripeProvider(BasePaymentProvider):
    def __init__(self):
        stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)

    def create_payment_session(self, order):
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': order.currency.lower(),
                    'product_data': {
                        'name': f"Billets pour {order.event.title}",
                    },
                    'unit_amount': int(order.total_amount * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{settings.SUPABASE_PUBLIC_URL}/payment/success?order_id={order.id}",
            cancel_url=f"{settings.SUPABASE_PUBLIC_URL}/payment/cancel?order_id={order.id}",
            metadata={'order_id': str(order.id)}
        )
        return session.url

    def verify_webhook(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
            return event
        except ValueError:
            return None
        except stripe.error.SignatureVerificationError:
            return None

    def handle_webhook(self, payload):
        if payload['type'] == 'checkout.session.completed':
            session = payload['data']['object']
            return {
                'order_id': session['metadata']['order_id'],
                'transaction_id': session['payment_intent'],
                'status': 'succeeded',
                'raw_data': session
            }
        return None
