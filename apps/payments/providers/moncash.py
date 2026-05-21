import requests
from django.conf import settings
from .base import BasePaymentProvider

class MonCashProvider(BasePaymentProvider):
    def __init__(self):
        self.client_id = getattr(settings, 'MONCASH_CLIENT_ID', None)
        self.secret_key = getattr(settings, 'MONCASH_SECRET_KEY', None)
        self.mode = getattr(settings, 'MONCASH_MODE', 'sandbox') # sandbox or live
        self.base_url = "https://sandbox.moncash.com" if self.mode == 'sandbox' else "https://moncash.com"

    def _get_token(self):
        auth_url = f"{self.base_url}/oauth/token"
        response = requests.post(
            auth_url,
            auth=(self.client_id, self.secret_key),
            data={'grant_type': 'client_credentials'}
        )
        return response.json().get('access_token')

    def create_payment_session(self, order):
        token = self._get_token()
        payment_url = f"{self.base_url}/v1/CreatePayment"

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        payload = {
            'amount': float(order.total_amount),
            'orderId': str(order.id)
        }

        response = requests.post(payment_url, json=payload, headers=headers)
        payment_data = response.json()

        # MonCash returns a redirect token
        redirect_token = payment_data.get('payment_token', {}).get('token')
        if redirect_token:
            return f"{self.base_url}/Payment/Redirect?token={redirect_token}"
        return None

    def verify_webhook(self, request):
        # MonCash webhook verification logic (IP checking or signature)
        # For now, we assume standard payload check
        return request.data

    def handle_webhook(self, payload):
        # MonCash specific logic
        # Example payload: {"transaction_id": "...", "order_id": "...", "status": "..."}
        if payload.get('status') == 'success':
            return {
                'order_id': payload.get('order_id'),
                'transaction_id': payload.get('transaction_id'),
                'status': 'succeeded',
                'raw_data': payload
            }
        return None
