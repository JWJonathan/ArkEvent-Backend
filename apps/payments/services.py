from django.db import transaction
from .models import Order, Payment, OrderItem
from apps.tickets.services import TicketService
from apps.core.tasks import send_ticket_confirmation_email

class PaymentService:
    @staticmethod
    def process_successful_payment(order_id, gateway, transaction_id, provider_response, metadata=None):
        with transaction.atomic():
            # Idempotency check: check if this transaction was already processed
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
                gateway=gateway,
                transaction_id=transaction_id,
                status='succeeded',
                provider_response=provider_response,
                metadata=metadata or {}
            )

            # Update order status
            order.status = 'paid'
            order.save()

            # Generate tickets
            for item in order.items.all():
                for _ in range(item.quantity):
                    ticket = TicketService.generate_ticket(
                        ticket_type_id=item.ticket_type.id,
                        owner_id=order.user_id,
                        order_id=order.id
                    )
                    send_ticket_confirmation_email.delay(ticket.id)

            return order
