from django.db import transaction
from .models import Order, Payment
from apps.tickets.models import Ticket
from django.utils import timezone

class PaymentService:
    @staticmethod
    def process_successful_payment(order_id, provider_name, transaction_id, raw_data):
        with transaction.atomic():
            # Idempotency check
            if Payment.objects.filter(transaction_id=transaction_id, status='succeeded').exists():
                return Order.objects.get(id=order_id)

            order = Order.objects.select_for_update().get(id=order_id)
            if order.status == 'paid':
                return order

            # Create payment record
            Payment.objects.create(
                order=order,
                user_id=order.user_id,
                amount=order.total_amount,
                currency=order.currency,
                transaction_id=transaction_id,
                status='succeeded',
                metadata={
                    'provider': provider_name,
                    'raw_data': raw_data
                }
            )

            # Update order status
            order.status = 'paid'
            order.save()

            # Confirm all reserved tickets for this order
            tickets = Ticket.objects.filter(order=order, status='reserved')
            for ticket in tickets:
                ticket.status = 'confirmed'
                ticket.reserved_until = None
                ticket.save()

            return order
