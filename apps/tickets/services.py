import qrcode
import base64
from io import BytesIO
import secrets
from .models import Ticket, TicketType
from django.db import transaction

class TicketService:
    @staticmethod
    def generate_ticket(ticket_type_id, owner_id, order_id=None):
        with transaction.atomic():
            ticket_type = TicketType.objects.select_for_update().get(id=ticket_type_id)
            if ticket_type.sold_count >= ticket_type.quantity:
                raise Exception("Ticket type sold out")

            token = secrets.token_urlsafe(32)
            ticket = Ticket.objects.create(
                ticket_type=ticket_type,
                owner_id=owner_id,
                order_id=order_id,
                token=token,
                status='valid'
            )

            ticket_type.sold_count += 1
            ticket_type.save()

            return ticket

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

    @staticmethod
    def validate_checkin(token):
        try:
            ticket = Ticket.objects.get(token=token)
            if ticket.status != 'valid':
                return False, f"Ticket is {ticket.status}"

            ticket.status = 'used'
            from django.utils import timezone
            ticket.checked_in_at = timezone.now()
            ticket.save()
            return True, "Check-in successful"
        except Ticket.DoesNotExist:
            return False, "Invalid ticket token"
