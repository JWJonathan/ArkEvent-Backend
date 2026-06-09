from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import secrets
import qrcode
import base64
from io import BytesIO
from .models import Ticket, TicketType
from apps.payments.models import Order, OrderItem
from apps.notifications.services import NotificationService

class TicketService:
    @staticmethod
    def generate_qr_base64(token):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(token)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

class ReservationService:
    @staticmethod
    def reserve_tickets(user_id, event_id, items_data):
        """
        items_data: list of dicts with {'ticket_type_id': uuid, 'quantity': int}
        """
        with transaction.atomic():
            # Calculate total amount and check availability
            total_amount = 0
            order_items_to_create = []
            tickets_to_create = []

            from apps.events.models import Event
            event = Event.objects.get(id=event_id)

            # Create the order first
            order = Order.objects.create(
                user_id=user_id,
                event=event,
                total_amount=0, # Will update later
                currency=event.currency,
                status='pending'
            )

            reserved_until = timezone.now() + timedelta(minutes=30)

            for item in items_data:
                tt_id = item['ticket_type_id']
                qty = item['quantity']

                # Lock the ticket type for update to prevent race conditions
                ticket_type = TicketType.objects.select_for_update().get(id=tt_id)

                # Calculate current availability
                # Sold tickets + Currently reserved (not expired) tickets
                sold_count = Ticket.objects.filter(ticket_type=ticket_type, status='confirmed').count()
                reserved_count = Ticket.objects.filter(
                    ticket_type=ticket_type,
                    status='reserved',
                    reserved_until__gt=timezone.now()
                ).count()

                available = ticket_type.quantity - (sold_count + reserved_count)

                if qty > available:
                    raise Exception(f"Not enough tickets available for {ticket_type.name}. Requested: {qty}, Available: {available}")

                total_amount += ticket_type.price * qty

                order_items_to_create.append(OrderItem(
                    order=order,
                    ticket_type=ticket_type,
                    quantity=qty,
                    price_at_purchase=ticket_type.price
                ))

                for _ in range(qty):
                    tickets_to_create.append(Ticket(
                        ticket_type=ticket_type,
                        order=order,
                        owner_id=user_id,
                        status='reserved',
                        token=secrets.token_urlsafe(32),
                        reserved_until=reserved_until
                    ))

            # Batch create
            OrderItem.objects.bulk_create(order_items_to_create)
            Ticket.objects.bulk_create(tickets_to_create)

    @staticmethod
    def claim_free_ticket(user_id, ticket_type_id):
        """
        Permet à un utilisateur d'obtenir un billet gratuit directement.
        """
        with transaction.atomic():
            ticket_type = TicketType.objects.select_for_update().get(id=ticket_type_id)
            
            if ticket_type.price > 0:
                raise Exception("Ce billet n'est pas gratuit.")

            # Vérifier disponibilité
            sold_count = Ticket.objects.filter(ticket_type=ticket_type, status='confirmed').count()
            reserved_count = Ticket.objects.filter(
                ticket_type=ticket_type,
                status='reserved',
                reserved_until__gt=timezone.now()
            ).count()

            available = ticket_type.quantity - (sold_count + reserved_count)
            if available <= 0:
                raise Exception("Plus de billets disponibles pour ce type.")

            from apps.events.models import Event
            event = ticket_type.event

            # Créer une commande marquée comme payée pour le suivi
            order = Order.objects.create(
                user_id=user_id,
                event=event,
                total_amount=0,
                currency=event.currency,
                status='paid'
            )

            OrderItem.objects.create(
                order=order,
                ticket_type=ticket_type,
                quantity=1,
                price_at_purchase=0
            )

            ticket = Ticket.objects.create(
                ticket_type=ticket_type,
                order=order,
                owner_id=user_id,
                status='confirmed',
                token=secrets.token_urlsafe(32)
            )

            # Notification
            NotificationService.notify_ticket_purchase(ticket.owner, order)
            
            return ticket
