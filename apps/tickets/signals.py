# tickets/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import TicketType, Ticket
import secrets

@receiver(post_save, sender=TicketType)
def generate_tickets_for_type(sender, instance, created, **kwargs):
    if created:
        tickets = []
        for _ in range(instance.quantity):
            tickets.append(Ticket(
                ticket_type=instance,
                token=secrets.token_hex(24),
                price=instance.price
            ))
        Ticket.objects.bulk_create(tickets)

@receiver(post_save, sender=Ticket)
def generate_ticket_qr_code(sender, instance, created, **kwargs):
    # On génère le QR code si le billet est vendu/confirmé et n'a pas encore de QR code
    if instance.status in ['sold', 'confirmed'] and not instance.qr_code:
        instance.generate_qr_code()
        # On génère aussi le PDF juste après avoir eu le QR code
        instance.generate_pdf_ticket()
        instance.save(update_fields=['qr_code', 'pdf_ticket'])
