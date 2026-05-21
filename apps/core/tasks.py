from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from apps.tickets.models import Ticket
from apps.tickets.services import TicketService

@shared_task
def send_ticket_confirmation_email(ticket_id):
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        # In a real app, we would get the user's email from their profile or order
        # For now, this is a placeholder
        subject = f"Confirmation de votre ticket pour {ticket.ticket_type.event.title}"
        qr_code = TicketService.generate_qr_base64(ticket.token)
        message = f"Merci pour votre achat. Voici votre ticket: {ticket.id}"

        # send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_email])
        print(f"Sending email for ticket {ticket_id}")
    except Ticket.DoesNotExist:
        pass

@shared_task
def process_async_webhook(payload, gateway):
    # Logic to process webhooks asynchronously if needed
    pass
